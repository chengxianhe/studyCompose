package com.study.cc.feature.home

import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.Preview
import com.study.cc.core.designsystem.theme.AppTheme
import com.study.cc.domain.model.DailySummary
import com.study.cc.domain.model.ResearchSignal

private val previewSignals =
    listOf(
        ResearchSignal(
            id = "evt-600001",
            stockCode = "600001",
            stockName = "Sample Co One",
            eventTitle = "Sample event title one",
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
            stockName = "Sample Co Two",
            eventTitle = "Sample event title two",
            eventScore = 79,
            businessRelevancePercent = 65,
            recentPriceChangePercent = -1.4,
            sectorPriceChangePercent = 3.2,
            historicalSimilarEventCount = 21,
            historicalPositiveReturnRatioPercent = 57.0,
        ),
    )

private val previewSummary =
    DailySummary(scannedNewsCount = 1836, mergedEventCount = 126, effectiveEventCount = 24, coreCandidateCount = 2)

@Preview(showBackground = true)
@Composable
internal fun HomeScreenDataPreview() {
    AppTheme {
        HomeScreen(
            uiState = HomeUiState(summary = previewSummary, signals = previewSignals, isLoading = false),
            onRefreshClick = {},
            onRetryClick = {},
        )
    }
}

@Preview(showBackground = true)
@Composable
internal fun HomeScreenLoadingPreview() {
    AppTheme {
        HomeScreen(
            uiState = HomeUiState(isLoading = true),
            onRefreshClick = {},
            onRetryClick = {},
        )
    }
}

@Preview(showBackground = true)
@Composable
internal fun HomeScreenEmptyPreview() {
    AppTheme {
        HomeScreen(
            uiState = HomeUiState(signals = emptyList(), isLoading = false),
            onRefreshClick = {},
            onRetryClick = {},
        )
    }
}

@Preview(showBackground = true)
@Composable
internal fun HomeScreenErrorPreview() {
    AppTheme {
        HomeScreen(
            uiState = HomeUiState(isLoading = false, hasError = true),
            onRefreshClick = {},
            onRetryClick = {},
        )
    }
}
