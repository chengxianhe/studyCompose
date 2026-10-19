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

class GetHomeSummaryUseCaseTest {
    private class FakeResearchSignalRepository(private val summary: DailySummary) : ResearchSignalRepository {
        override fun observeDailySummary(): Flow<DailySummary> = flowOf(summary)

        override fun observeSignals(): Flow<List<ResearchSignal>> = flowOf(emptyList())

        override suspend fun refresh() = Unit
    }

    @Test
    fun `invoke 返回 repository 里的汇总数据`() =
        runTest {
            val summary =
                DailySummary(
                    scannedNewsCount = 10,
                    mergedEventCount = 5,
                    effectiveEventCount = 2,
                    coreCandidateCount = 1,
                )
            val useCase = GetHomeSummaryUseCase(FakeResearchSignalRepository(summary))

            val result = useCase().first()

            assertThat(result).isEqualTo(summary)
        }
}
