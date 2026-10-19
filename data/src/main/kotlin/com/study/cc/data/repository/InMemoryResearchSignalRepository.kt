package com.study.cc.data.repository

import com.study.cc.domain.model.DailySummary
import com.study.cc.domain.model.ResearchSignal
import com.study.cc.domain.repository.ResearchSignalRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject

private val seedSummary =
    DailySummary(
        scannedNewsCount = 1836,
        mergedEventCount = 126,
        effectiveEventCount = 24,
        coreCandidateCount = 2,
    )

private val seedSignals =
    listOf(
        ResearchSignal(
            id = "evt-600001",
            stockCode = "600001",
            stockName = "Sample Resources Co",
            eventTitle = "Overseas antimony mine suspends production",
            eventScore = 88,
            businessRelevancePercent = 92,
            recentPriceChangePercent = 2.1,
            sectorPriceChangePercent = 10.4,
            historicalSimilarEventCount = 47,
            historicalPositiveReturnRatioPercent = 68.1,
        ),
        ResearchSignal(
            id = "evt-600002",
            stockCode = "600002",
            stockName = "Sample Chemicals Co",
            eventTitle = "Overseas TDI plant halts output",
            eventScore = 79,
            businessRelevancePercent = 65,
            recentPriceChangePercent = -1.4,
            sectorPriceChangePercent = 3.2,
            historicalSimilarEventCount = 21,
            historicalPositiveReturnRatioPercent = 57.0,
        ),
    )

internal class InMemoryResearchSignalRepository @Inject constructor() : ResearchSignalRepository {
    private val summary = MutableStateFlow(seedSummary)
    private val signals = MutableStateFlow(seedSignals)

    override fun observeDailySummary(): Flow<DailySummary> = summary.asStateFlow()

    override fun observeSignals(): Flow<List<ResearchSignal>> = signals.asStateFlow()

    override suspend fun refresh() {
        delay(REFRESH_DELAY_MS)
        summary.value = seedSummary
        signals.value = seedSignals
    }

    private companion object {
        const val REFRESH_DELAY_MS = 600L
    }
}
