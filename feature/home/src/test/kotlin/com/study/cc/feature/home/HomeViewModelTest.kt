package com.study.cc.feature.home

import app.cash.turbine.test
import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.DailySummary
import com.study.cc.domain.model.ResearchSignal
import com.study.cc.domain.repository.ResearchSignalRepository
import com.study.cc.domain.usecase.GetHomeSummaryUseCase
import com.study.cc.domain.usecase.GetResearchSignalsUseCase
import com.study.cc.domain.usecase.RefreshResearchSignalsUseCase
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModelTest {
    private val emptySummary =
        DailySummary(scannedNewsCount = 0, mergedEventCount = 0, effectiveEventCount = 0, coreCandidateCount = 0)

    private val signal =
        ResearchSignal(
            id = "evt-600001",
            stockCode = "600001",
            stockName = "t",
            eventTitle = "e",
            eventScore = 80,
            businessRelevancePercent = 90,
            recentPriceChangePercent = 1.0,
            sectorPriceChangePercent = 2.0,
            historicalSimilarEventCount = 3,
            historicalPositiveReturnRatioPercent = 60.0,
        )

    private class FakeResearchSignalRepository(
        var signalsFlow: Flow<List<ResearchSignal>>,
        private val summary: DailySummary,
        private val onRefresh: suspend () -> Unit = {},
    ) : ResearchSignalRepository {
        var refreshCount = 0
            private set

        override fun observeDailySummary(): Flow<DailySummary> = MutableStateFlow(summary)

        override fun observeSignals(): Flow<List<ResearchSignal>> = signalsFlow

        override suspend fun refresh() {
            refreshCount++
            onRefresh()
        }
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
    fun `加载中先 isLoading 随后数据到达后展示信号列表`() =
        runTest {
            val signals = MutableSharedFlow<List<ResearchSignal>>()
            val viewModel = viewModel(FakeResearchSignalRepository(signals, emptySummary))

            viewModel.uiState.test {
                assertThat(awaitItem().isLoading).isTrue()

                signals.emit(listOf(signal))

                val loaded = awaitItem()
                assertThat(loaded.isLoading).isFalse()
                assertThat(loaded.signals).containsExactly(signal)
            }
        }

    @Test
    fun `加载中数据流报错后 isLoading 结束并进入错误态`() =
        runTest {
            val signals = MutableSharedFlow<List<ResearchSignal>>()
            val failing = signals.onEach { error("boom") }
            val viewModel = viewModel(FakeResearchSignalRepository(failing, emptySummary))

            viewModel.uiState.test {
                assertThat(awaitItem().isLoading).isTrue()

                signals.emit(listOf(signal))

                val failed = awaitItem()
                assertThat(failed.isLoading).isFalse()
                assertThat(failed.hasError).isTrue()
            }
        }

    @Test
    fun `刷新失败时 hasError 被写入 state 且 isRefreshing 复位`() =
        runTest {
            val repository =
                FakeResearchSignalRepository(
                    signalsFlow = MutableStateFlow(emptyList()),
                    summary = emptySummary,
                    onRefresh = { throw IllegalStateException("boom") },
                )
            val viewModel = viewModel(repository)

            viewModel.onRefreshClick()

            val state = viewModel.uiState.value
            assertThat(state.hasError).isTrue()
            assertThat(state.isRefreshing).isFalse()
        }

    @Test
    fun `数据流报错后点重试会重新订阅并恢复数据`() =
        runTest {
            val repository =
                FakeResearchSignalRepository(
                    signalsFlow = flow { throw IllegalStateException("boom") },
                    summary = emptySummary,
                )
            val viewModel = viewModel(repository)
            assertThat(viewModel.uiState.value.hasError).isTrue()

            repository.signalsFlow = MutableStateFlow(listOf(signal))
            viewModel.onRetryClick()

            val state = viewModel.uiState.value
            assertThat(state.hasError).isFalse()
            assertThat(state.isLoading).isFalse()
            assertThat(state.signals).containsExactly(signal)
            assertThat(repository.refreshCount).isEqualTo(1)
        }

    @Test
    fun `刷新进行中再次点击不会重复触发`() =
        runTest {
            val gate = CompletableDeferred<Unit>()
            val repository =
                FakeResearchSignalRepository(
                    signalsFlow = MutableStateFlow(emptyList()),
                    summary = emptySummary,
                    onRefresh = { gate.await() },
                )
            val viewModel = viewModel(repository)

            viewModel.onRefreshClick()
            viewModel.onRefreshClick()

            assertThat(viewModel.uiState.value.isRefreshing).isTrue()
            assertThat(repository.refreshCount).isEqualTo(1)

            gate.complete(Unit)

            assertThat(viewModel.uiState.value.isRefreshing).isFalse()
        }

    private fun viewModel(repository: ResearchSignalRepository): HomeViewModel =
        HomeViewModel(
            getHomeSummaryUseCase = GetHomeSummaryUseCase(repository),
            getResearchSignalsUseCase = GetResearchSignalsUseCase(repository),
            refreshResearchSignalsUseCase = RefreshResearchSignalsUseCase(repository),
        )
}
