package com.study.cc.domain.usecase

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.DailySummary
import com.study.cc.domain.model.ResearchSignal
import com.study.cc.domain.repository.ResearchSignalRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Test

class RefreshResearchSignalsUseCaseTest {
    private class FakeResearchSignalRepository : ResearchSignalRepository {
        var refreshCallCount = 0
            private set

        override fun observeDailySummary(): Flow<DailySummary> =
            flowOf(
                DailySummary(
                    scannedNewsCount = 0,
                    mergedEventCount = 0,
                    effectiveEventCount = 0,
                    coreCandidateCount = 0,
                ),
            )

        override fun observeSignals(): Flow<List<ResearchSignal>> = flowOf(emptyList())

        override suspend fun refresh() {
            refreshCallCount += 1
        }
    }

    @Test
    fun `invoke 委托给 repository refresh`() =
        runTest {
            val repository = FakeResearchSignalRepository()
            val useCase = RefreshResearchSignalsUseCase(repository)

            useCase()

            assertThat(repository.refreshCallCount).isEqualTo(1)
        }
}
