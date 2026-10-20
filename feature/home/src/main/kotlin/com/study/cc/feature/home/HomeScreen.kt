package com.study.cc.feature.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.study.cc.core.designsystem.theme.Spacing
import com.study.cc.core.ui.state.EmptyState
import com.study.cc.core.ui.state.ErrorState
import com.study.cc.core.ui.state.LoadingState
import com.study.cc.domain.model.DailySummary
import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.ResearchSignal
import java.util.Locale

@Composable
fun HomeRoute(modifier: Modifier = Modifier, viewModel: HomeViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    HomeScreen(
        uiState = uiState,
        onRefreshClick = viewModel::onRefreshClick,
        onRetryClick = viewModel::onRetryClick,
        modifier = modifier,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    uiState: HomeUiState,
    onRefreshClick: () -> Unit,
    onRetryClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Scaffold(
        modifier = modifier,
        topBar = { HomeTopBar(isRefreshing = uiState.isRefreshing, onRefreshClick = onRefreshClick) },
    ) { innerPadding ->
        HomeContent(
            uiState = uiState,
            onRetryClick = onRetryClick,
            modifier = Modifier.padding(innerPadding),
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun HomeTopBar(isRefreshing: Boolean, onRefreshClick: () -> Unit) {
    TopAppBar(
        title = { Text(text = stringResource(R.string.home_title)) },
        actions = {
            TextButton(onClick = onRefreshClick) {
                Text(
                    text =
                    if (isRefreshing) {
                        stringResource(R.string.home_refreshing_label)
                    } else {
                        stringResource(R.string.home_refresh_action)
                    },
                )
            }
        },
    )
}

@Composable
private fun HomeContent(uiState: HomeUiState, onRetryClick: () -> Unit, modifier: Modifier = Modifier) {
    when {
        uiState.isLoading -> LoadingState(modifier = modifier)
        uiState.hasError ->
            ErrorState(
                message = stringResource(R.string.home_error_message),
                retryLabel = stringResource(R.string.home_retry_action),
                onRetryClick = onRetryClick,
                modifier = modifier,
            )
        uiState.signals.isEmpty() && uiState.summary == null ->
            EmptyState(
                message = stringResource(R.string.home_empty_message),
                modifier = modifier,
            )
        else ->
            HomeSignalList(
                summary = uiState.summary,
                signals = uiState.signals,
                quotes = uiState.quotes,
                modifier = modifier,
            )
    }
}

@Composable
private fun HomeSignalList(
    summary: DailySummary?,
    signals: List<ResearchSignal>,
    quotes: Map<String, Quote>,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(Spacing.lg),
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
    ) {
        if (summary != null) {
            item { HomeSummaryRow(summary) }
        }
        if (signals.isEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.home_empty_message),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        items(signals, key = ResearchSignal::id) { signal -> SignalCard(signal, quotes[signal.id]) }
    }
}

@Composable
private fun HomeSummaryRow(summary: DailySummary, modifier: Modifier = Modifier) {
    Row(modifier = modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        SummaryStat(value = summary.scannedNewsCount, label = stringResource(R.string.home_summary_scanned))
        SummaryStat(value = summary.mergedEventCount, label = stringResource(R.string.home_summary_merged))
        SummaryStat(value = summary.effectiveEventCount, label = stringResource(R.string.home_summary_effective))
        SummaryStat(value = summary.coreCandidateCount, label = stringResource(R.string.home_summary_candidates))
    }
}

@Composable
private fun SummaryStat(value: Int, label: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text = value.toString(), style = MaterialTheme.typography.titleLarge)
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun SignalCard(signal: ResearchSignal, quote: Quote?, modifier: Modifier = Modifier) {
    Column(modifier = modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(text = signal.eventScore.toString(), style = MaterialTheme.typography.titleLarge)
            Text(text = "${signal.stockName} ${signal.stockCode}", style = MaterialTheme.typography.titleMedium)
        }
        Text(text = signal.eventTitle, style = MaterialTheme.typography.bodyMedium)
        SignalMetricsRow(signal)
        if (quote != null) {
            Text(
                text =
                stringResource(
                    R.string.home_signal_quote,
                    String.format(Locale.US, "%.2f", quote.price),
                    formatSignedPercent(quote.changePercent),
                ),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun SignalMetricsRow(signal: ResearchSignal, modifier: Modifier = Modifier) {
    val metrics =
        listOf(
            stringResource(R.string.home_signal_relevance, signal.businessRelevancePercent),
            stringResource(R.string.home_signal_recent_change, formatSignedPercent(signal.recentPriceChangePercent)),
            stringResource(R.string.home_signal_sector_change, formatSignedPercent(signal.sectorPriceChangePercent)),
            stringResource(R.string.home_signal_history, signal.historicalSimilarEventCount),
            stringResource(
                R.string.home_signal_positive_ratio,
                formatPercent(signal.historicalPositiveReturnRatioPercent),
            ),
        )
    Column(modifier = modifier) {
        metrics.forEach { metric ->
            Text(
                text = metric,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

private fun formatSignedPercent(value: Double): String {
    val sign = if (value >= 0) "+" else ""
    return "$sign${formatPercent(value)}%"
}

private fun formatPercent(value: Double): String = String.format(Locale.US, "%.1f", value)
