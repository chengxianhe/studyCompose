package com.study.cc.feature.home

import com.google.common.truth.Truth.assertThat
import com.study.cc.core.logging.Logger
import com.study.cc.domain.model.DailySummary
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class HomeQuoteViewModelTest {
    private val firstSignal = testSignal("first", "600001")
    private val secondSignal = testSignal("second", "000001")

    @Before
    fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun allQuotesLoadBySignalId() = runTest {
        val repository = SignalRepository(listOf(firstSignal, secondSignal))
        val viewModel = homeViewModel(repository) { security -> testQuote(security) }

        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("first", "second")
        assertThat(viewModel.uiState.value.quotes["first"]?.security?.code).isEqualTo("600001")
        assertThat(viewModel.uiState.value.quotes["second"]?.security?.code).isEqualTo("000001")
        assertThat(viewModel.uiState.value.hasError).isFalse()
    }

    @Test
    fun oneQuoteFailureLeavesOtherQuoteVisible() = runTest {
        val repository = SignalRepository(listOf(firstSignal, secondSignal))
        val viewModel =
            homeViewModel(repository) { security ->
                if (security.code == "600001") error("Unavailable")
                testQuote(security)
            }

        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("second")
        assertThat(viewModel.uiState.value.hasError).isFalse()
    }

    @Test
    fun allQuoteFailuresDoNotSetPageError() = runTest {
        val viewModel = homeViewModel(SignalRepository(listOf(firstSignal, secondSignal))) { error("Unavailable") }

        assertThat(viewModel.uiState.value.quotes).isEmpty()
        assertThat(viewModel.uiState.value.hasError).isFalse()
    }

    @Test
    fun unresolvableBeijingCodeSkipsQuoteRequest() = runTest {
        var calls = 0
        val viewModel = homeViewModel(SignalRepository(listOf(testSignal("beijing", "800001")))) { security ->
            calls++
            testQuote(security)
        }

        assertThat(calls).isEqualTo(0)
        assertThat(viewModel.uiState.value.quotes).isEmpty()
        assertThat(viewModel.uiState.value.hasError).isFalse()
    }

    @Test
    fun refreshReloadsQuoteEvenWhenSignalListDoesNotEmitAgain() = runTest {
        var calls = 0
        val viewModel = homeViewModel(SignalRepository(listOf(firstSignal))) { security ->
            calls++
            testQuote(security, calls.toDouble())
        }
        assertThat(viewModel.uiState.value.quotes["first"]?.price).isEqualTo(1.0)

        viewModel.onRefreshClick()

        assertThat(calls).isEqualTo(2)
        assertThat(viewModel.uiState.value.quotes["first"]?.price).isEqualTo(2.0)
    }

    @Test
    fun refreshKeepsPreviousQuoteVisibleUntilNewOneArrives() = runTest {
        var calls = 0
        val gate = CompletableDeferred<Unit>()
        val viewModel = homeViewModel(SignalRepository(listOf(firstSignal))) { security ->
            calls++
            if (calls > 1) gate.await()
            testQuote(security, calls.toDouble())
        }
        assertThat(viewModel.uiState.value.quotes["first"]?.price).isEqualTo(1.0)

        viewModel.onRefreshClick()

        assertThat(viewModel.uiState.value.quotes["first"]?.price).isEqualTo(1.0)
        gate.complete(Unit)
        assertThat(viewModel.uiState.value.quotes["first"]?.price).isEqualTo(2.0)
    }

    @Test
    fun summaryChangeDoesNotReloadUnchangedSignals() = runTest {
        var calls = 0
        val repository = SignalRepository(listOf(firstSignal))
        val viewModel = homeViewModel(repository) { security ->
            calls++
            testQuote(security)
        }

        repository.summary.value = DailySummary(1, 0, 0, 0)

        assertThat(calls).isEqualTo(1)
        assertThat(viewModel.uiState.value.summary).isEqualTo(repository.summary.value)
    }

    @Test
    fun newSignalListCancelsPreviousQuoteLoad() = runTest {
        val repository = SignalRepository(listOf(firstSignal))
        val cancelled = CompletableDeferred<Unit>()
        val viewModel = homeViewModel(repository) { security ->
            if (security.code == "600001") {
                try {
                    awaitCancellation()
                } finally {
                    cancelled.complete(Unit)
                }
            }
            testQuote(security)
        }

        repository.signals.value = listOf(secondSignal)

        assertThat(cancelled.isCompleted).isTrue()
        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("second")
    }

    @Test
    fun strayCancellationIsNotLoggedAsFailureAndOtherCardsStillLoad() = runTest {
        val logged = mutableListOf<Throwable?>()
        val logger = object : Logger by NoOpLogger {
            override fun w(tag: String, message: String, throwable: Throwable?) {
                logged += throwable
            }
        }
        val viewModel = homeViewModel(SignalRepository(listOf(firstSignal, secondSignal)), logger) { security ->
            if (security.code == "600001") throw CancellationException("Cancelled")
            testQuote(security)
        }

        assertThat(logged).isEmpty()
        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("second")
        assertThat(viewModel.uiState.value.hasError).isFalse()
    }

    @Test
    fun retryReloadsQuotes() = runTest {
        var calls = 0
        val viewModel = homeViewModel(SignalRepository(listOf(firstSignal))) { security ->
            calls++
            testQuote(security, calls.toDouble())
        }

        viewModel.onRetryClick()

        assertThat(calls).isEqualTo(2)
        assertThat(viewModel.uiState.value.quotes["first"]?.price).isEqualTo(2.0)
    }
}
