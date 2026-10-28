package com.study.cc.feature.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.study.cc.core.designsystem.theme.Spacing
import com.study.cc.core.ui.state.ErrorState
import com.study.cc.domain.model.LibrarySyncState
import com.study.cc.domain.model.PhotoAccess
import com.study.cc.domain.model.SyncStatus

/** Minimal access and sync status panel; the real photo UI replaces it in later tasks. */
@Composable
fun LibraryAccessPanel(
    library: LibrarySyncState,
    onGrantClick: () -> Unit,
    onRetryClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    when {
        library.status is SyncStatus.Failed ->
            ErrorState(
                message = stringResource(R.string.home_sync_failed_message),
                retryLabel = stringResource(R.string.home_retry_action),
                onRetryClick = onRetryClick,
                modifier = modifier,
            )
        library.access == PhotoAccess.NONE ->
            PanelColumn(modifier) {
                Text(text = stringResource(R.string.home_access_required_message))
                Button(onClick = onGrantClick) { Text(text = stringResource(R.string.home_access_grant_action)) }
            }
        else -> SyncSummary(library, onGrantClick, modifier)
    }
}

@Composable
private fun SyncSummary(library: LibrarySyncState, onGrantClick: () -> Unit, modifier: Modifier) {
    PanelColumn(modifier) {
        Text(
            text = stringResource(R.string.home_library_count, library.itemCount),
            style = MaterialTheme.typography.titleMedium,
        )
        SyncProgress(library.status)
        if (library.access == PhotoAccess.PARTIAL) {
            Text(
                text = stringResource(R.string.home_access_partial_message),
                color = MaterialTheme.colorScheme.error,
            )
            Button(onClick = onGrantClick) { Text(text = stringResource(R.string.home_access_partial_action)) }
        }
    }
}

@Composable
private fun SyncProgress(status: SyncStatus) {
    val syncing = status as? SyncStatus.Syncing ?: return
    val total = syncing.total
    if (total == null || total == 0) {
        Text(text = stringResource(R.string.home_sync_progress_unknown, syncing.processed))
        LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
    } else {
        Text(text = stringResource(R.string.home_sync_progress, syncing.processed, total))
        LinearProgressIndicator(progress = { syncing.processed.toFloat() / total }, modifier = Modifier.fillMaxWidth())
    }
}

@Composable
private fun PanelColumn(modifier: Modifier, content: @Composable () -> Unit) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(Spacing.lg),
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
    ) {
        content()
    }
}
