package com.study.cc.feature.library

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import coil.ImageLoader
import com.study.cc.core.designsystem.component.AppButton
import com.study.cc.core.designsystem.theme.Spacing
import com.study.cc.core.ui.state.EmptyState
import com.study.cc.core.ui.state.ErrorState
import com.study.cc.core.ui.state.LoadingState
import com.study.cc.domain.model.PhotoAccess
import com.study.cc.domain.model.SyncStatus

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PhotoDayScreen(
    uiState: PhotoDayUiState,
    imageLoader: ImageLoader,
    actions: PhotoDayActions,
    modifier: Modifier = Modifier,
) {
    Scaffold(
        modifier = modifier,
        topBar = { TopAppBar(title = { Text(text = stringResource(R.string.library_day_title)) }) },
    ) { innerPadding ->
        val contentModifier = Modifier.padding(innerPadding)
        when {
            uiState.library.access == PhotoAccess.NONE -> EmptyState(
                message = stringResource(R.string.library_day_access_required),
                actionLabel = stringResource(R.string.library_day_grant_action),
                onActionClick = actions.onGrantClick,
                modifier = contentModifier,
            )
            uiState.loadFailed ||
                (uiState.library.status is SyncStatus.Failed && uiState.buckets.isEmpty()) -> ErrorState(
                message = stringResource(R.string.library_day_load_failed),
                retryLabel = stringResource(R.string.library_day_retry),
                onRetryClick = actions.onRetryClick,
                modifier = contentModifier,
            )
            !uiState.bucketsLoaded || (uiState.buckets.isEmpty() && uiState.library.status is SyncStatus.Syncing) ->
                LoadingState(modifier = contentModifier)
            uiState.buckets.isEmpty() -> EmptyState(
                message = stringResource(R.string.library_day_empty),
                modifier = contentModifier,
            )
            else -> Column(modifier = contentModifier) {
                StatusNotice(uiState, actions.onGrantClick, actions.onRetryClick)
                PhotoDayGrid(
                    buckets = uiState.buckets,
                    itemsByDay = uiState.itemsByDay,
                    imageLoader = imageLoader,
                    onDaysVisible = actions.onDaysVisible,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun StatusNotice(uiState: PhotoDayUiState, onGrantClick: () -> Unit, onRetryClick: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        Text(
            text = stringResource(R.string.library_day_count, uiState.library.itemCount),
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(horizontal = Spacing.sm),
        )
        when {
            uiState.library.access == PhotoAccess.PARTIAL -> {
                Text(
                    text = stringResource(R.string.library_day_partial_access),
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(horizontal = Spacing.sm),
                )
                AppButton(label = stringResource(R.string.library_day_extend_access), onClick = onGrantClick)
            }
            uiState.library.status is SyncStatus.Failed -> {
                Text(
                    text = stringResource(R.string.library_day_sync_failed),
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(horizontal = Spacing.sm),
                )
                AppButton(label = stringResource(R.string.library_day_retry), onClick = onRetryClick)
            }
            uiState.library.status is SyncStatus.Syncing -> LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        }
    }
}
