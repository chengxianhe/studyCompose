package com.study.cc.domain.usecase

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.DailySummary
import com.study.cc.domain.model.ResearchSignal
import com.study.cc.domain.repository.ResearchSignalRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Test

class GetResearchSignalsUseCaseTest {
    private class FakeResearchSignalRepository(private val signals: List<ResearchSignal>) : ResearchSignalRepository {
        override fun observeDailySummary(): Flow<DailySummary> = flowOf(
            DailySummary(
                scannedNewsCount = 0,
                mergedEventCount = 0,
                effectiveEventCount = 0,
                coreCandidateCount = 0,
            ),
        )

        override fun observeSignals(): Flow<List<ResearchSignal>> = flowOf(signals)

        override suspend fun refresh() = Unit
    }

    @Test
    fun `invoke 返回 repository 里的信号列表`() = runTest {
        val signals =
            listOf(
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
                ),
            )
        val useCase = GetResearchSignalsUseCase(FakeResearchSignalRepository(signals))

        val result = useCase().first()

        assertThat(result).isEqualTo(signals)
    }
}
