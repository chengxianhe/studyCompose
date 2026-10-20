package com.study.cc.feature.home

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.DailySummary
import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.ResearchSignal
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.repository.ResearchSignalRepository
import com.study.cc.domain.usecase.GetHomeSummaryUseCase
import com.study.cc.domain.usecase.GetQuoteUseCase
import com.study.cc.domain.usecase.GetResearchSignalsUseCase
import com.study.cc.domain.usecase.RefreshResearchSignalsUseCase
import com.study.cc.domain.usecase.ResolveSecurityIdUseCase
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test
import java.time.Instant

private const val EVENT_SCORE = 80
private const val BUSINESS_RELEVANCE = 90
private const val SIMILAR_EVENT_COUNT = 3
private const val POSITIVE_RETURN_RATIO = 60.0

@OptIn(ExperimentalCoroutinesApi::class)
class HomeQuoteViewModelTest {
    private val firstSignal = signal("first", "600001")
    private val secondSignal = signal("second", "000001")

    private class SignalRepository(initial: List<ResearchSignal>) : ResearchSignalRepository {
        val signals = MutableStateFlow(initial)
        val summary = MutableStateFlow(DailySummary(0, 0, 0, 0))

        override fun observeDailySummary(): Flow<DailySummary> = summary

        override fun observeSignals(): Flow<List<ResearchSignal>> = signals

        override suspend fun refresh() = Unit
    }

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
        val viewModel = viewModel(repository) { security -> quote(security) }

        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("first", "second")
        assertThat(viewModel.uiState.value.quotes["first"]?.security?.code).isEqualTo("600001")
        assertThat(viewModel.uiState.value.quotes["second"]?.security?.code).isEqualTo("000001")
        assertThat(viewModel.uiState.value.hasError).isFalse()
    }

    @Test
    fun oneQuoteFailureLeavesOtherQuoteVisible() = runTest {
        val repository = SignalRepository(listOf(firstSignal, secondSignal))
        val viewModel =
            viewModel(repository) { security ->
                if (security.code == "600001") error("Unavailable")
                quote(security)
            }

        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("second")
        assertThat(viewModel.uiState.value.hasError).isFalse()
    }

    @Test
    fun allQuoteFailuresDoNotSetPageError() = runTest {
        val viewModel = viewModel(SignalRepository(listOf(firstSignal, secondSignal))) { error("Unavailable") }

        assertThat(viewModel.uiState.value.quotes).isEmpty()
        assertThat(viewModel.uiState.value.hasError).isFalse()
    }

    @Test
    fun unresolvableBeijingCodeSkipsQuoteRequest() = runTest {
        var calls = 0
        val viewModel = viewModel(SignalRepository(listOf(signal("beijing", "800001")))) { security ->
            calls++
            quote(security)
        }

        assertThat(calls).isEqualTo(0)
        assertThat(viewModel.uiState.value.quotes).isEmpty()
        assertThat(viewModel.uiState.value.hasError).isFalse()
    }

    @Test
    fun refreshReloadsQuoteEvenWhenSignalListDoesNotEmitAgain() = runTest {
        var calls = 0
        val viewModel = viewModel(SignalRepository(listOf(firstSignal))) { security ->
            calls++
            quote(security, calls.toDouble())
        }
        assertThat(viewModel.uiState.value.quotes["first"]?.price).isEqualTo(1.0)

        viewModel.onRefreshClick()

        assertThat(calls).isEqualTo(2)
        assertThat(viewModel.uiState.value.quotes["first"]?.price).isEqualTo(2.0)
    }

    @Test
    fun summaryChangeDoesNotReloadUnchangedSignals() = runTest {
        var calls = 0
        val repository = SignalRepository(listOf(firstSignal))
        val viewModel = viewModel(repository) { security ->
            calls++
            quote(security)
        }

        repository.summary.value = DailySummary(1, 0, 0, 0)

        assertThat(calls).isEqualTo(1)
        assertThat(viewModel.uiState.value.summary).isEqualTo(repository.summary.value)
    }

    @Test
    fun newSignalListCancelsPreviousQuoteLoad() = runTest {
        val repository = SignalRepository(listOf(firstSignal))
        val cancelled = CompletableDeferred<Unit>()
        val viewModel = viewModel(repository) { security ->
            if (security.code == "600001") {
                try {
                    awaitCancellation()
                } finally {
                    cancelled.complete(Unit)
                }
            }
            quote(security)
        }

        repository.signals.value = listOf(secondSignal)

        assertThat(cancelled.isCompleted).isTrue()
        assertThat(viewModel.uiState.value.quotes.keys).containsExactly("second")
    }

    @Test
    fun quoteCancellationCancelsSiblingAndDoesNotPublishPartialResults() = runTest {
        val gate = CompletableDeferred<Unit>()
        val siblingCancelled = CompletableDeferred<Unit>()
        val viewModel = viewModel(SignalRepository(listOf(firstSignal, secondSignal))) { security ->
            if (security.code == "600001") {
                gate.await()
                throw CancellationException("Cancelled")
            }
            try {
                awaitCancellation()
            } finally {
                siblingCancelled.complete(Unit)
            }
        }

        gate.complete(Unit)

        assertThat(siblingCancelled.isCompleted).isTrue()
        assertThat(viewModel.uiState.value.quotes).isEmpty()
        assertThat(viewModel.uiState.value.hasError).isFalse()
    }

    @Test
    fun retryReloadsQuotes() = runTest {
        var calls = 0
        val viewModel = viewModel(SignalRepository(listOf(firstSignal))) { security ->
            calls++
            quote(security, calls.toDouble())
        }

        viewModel.onRetryClick()

        assertThat(calls).isAtLeast(2)
        assertThat(viewModel.uiState.value.quotes["first"]?.price).isEqualTo(calls.toDouble())
    }

    private fun viewModel(
        repository: ResearchSignalRepository,
        onQuote: suspend (SecurityId) -> Quote,
    ): HomeViewModel = HomeViewModel(
        getHomeSummaryUseCase = GetHomeSummaryUseCase(repository),
        getResearchSignalsUseCase = GetResearchSignalsUseCase(repository),
        refreshResearchSignalsUseCase = RefreshResearchSignalsUseCase(repository),
        getQuoteUseCase = GetQuoteUseCase(FakeQuoteRepository(onQuote)),
        resolveSecurityIdUseCase = ResolveSecurityIdUseCase(),
    )

    private fun signal(id: String, code: String): ResearchSignal = ResearchSignal(
        id,
        code,
        "name",
        "event",
        EVENT_SCORE,
        BUSINESS_RELEVANCE,
        1.0,
        2.0,
        SIMILAR_EVENT_COUNT,
        POSITIVE_RETURN_RATIO,
    )

    private fun quote(security: SecurityId, price: Double = 1.0): Quote =
        Quote(security, "name", price, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 1, 1.0, 0.0, "test", Instant.EPOCH, Instant.EPOCH)
}
