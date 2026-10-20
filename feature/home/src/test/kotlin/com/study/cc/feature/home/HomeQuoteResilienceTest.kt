package com.study.cc.feature.home

import com.google.common.truth.Truth.assertThat
import com.study.cc.core.logging.Logger
import com.study.cc.domain.model.StockDataException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class HomeQuoteResilienceTest {
    private val firstSignal = testSignal("first", "600001")
    private val secondSignal = testSignal("second", "600002")

    @Before
    fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun slowQuoteDoesNotDelayFastQuote() = runTest {
        val gate = CompletableDeferred<Unit>()
        val viewModel = homeViewModel(SignalRepository(listOf(firstSignal, secondSignal))) { security ->
            if (security.code == "600002") gate.await()
            testQuote(security)
        }

        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("first")
        gate.complete(Unit)
        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("first", "second")
    }

    @Test
    fun unexpectedQuoteFailureIsLoggedButKnownOnesAreNot() = runTest {
        val logged = mutableListOf<Throwable?>()
        val logger = object : Logger by NoOpLogger {
            override fun w(tag: String, message: String, throwable: Throwable?) {
                logged += throwable
            }
        }
        homeViewModel(SignalRepository(listOf(firstSignal, secondSignal)), logger) { security ->
            if (security.code == "600001") throw StockDataException.NoData()
            error("unexpected")
        }

        assertThat(logged).hasSize(1)
        assertThat(logged.single()).isInstanceOf(IllegalStateException::class.java)
    }

    @Test
    fun failedReloadRemovesPreviousQuoteInsteadOfShowingStalePrice() = runTest {
        var calls = 0
        val viewModel = homeViewModel(SignalRepository(listOf(firstSignal))) { security ->
            if (++calls > 1) throw StockDataException.NoData()
            testQuote(security)
        }
        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("first")

        viewModel.onRefreshClick()

        assertThat(viewModel.uiState.value.quotes).isEmpty()
    }

    @Test
    fun quotesOfRemovedSignalsArePrunedAndOthersKeptWhileReloading() = runTest {
        val repository = SignalRepository(listOf(firstSignal, secondSignal))
        val gate = CompletableDeferred<Unit>()
        var calls = 0
        val viewModel = homeViewModel(repository) { security ->
            if (++calls > 2) gate.await()
            testQuote(security)
        }
        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("first", "second")

        repository.signals.value = listOf(secondSignal.copy(eventScore = 1))

        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("second")
        gate.complete(Unit)
    }
}
