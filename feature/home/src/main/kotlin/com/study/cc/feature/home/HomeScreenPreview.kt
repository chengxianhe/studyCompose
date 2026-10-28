package com.study.cc.feature.home

import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.Preview
import com.study.cc.core.designsystem.theme.AppTheme
import com.study.cc.domain.model.LibrarySyncState
import com.study.cc.domain.model.PhotoAccess
import com.study.cc.domain.model.SyncStatus

private const val PREVIEW_COUNT = 1408
private const val PREVIEW_PROCESSED = 600

@Composable
private fun PreviewHome(library: LibrarySyncState) {
    AppTheme {
        HomeScreen(uiState = HomeUiState(library), onGrantClick = {}, onRetryClick = {})
    }
}

@Preview(showBackground = true)
@Composable
internal fun HomeScreenNoAccessPreview() {
    PreviewHome(LibrarySyncState(PhotoAccess.NONE, SyncStatus.Idle, 0, null))
}

@Preview(showBackground = true)
@Composable
internal fun HomeScreenPartialSyncingPreview() {
    PreviewHome(
        LibrarySyncState(
            PhotoAccess.PARTIAL,
            SyncStatus.Syncing(PREVIEW_PROCESSED, PREVIEW_COUNT),
            PREVIEW_PROCESSED,
            null,
        ),
    )
}

@Preview(showBackground = true)
@Composable
internal fun HomeScreenFullPreview() {
    PreviewHome(LibrarySyncState(PhotoAccess.FULL, SyncStatus.Idle, PREVIEW_COUNT, null))
}

@Preview(showBackground = true)
@Composable
internal fun HomeScreenFailedPreview() {
    PreviewHome(LibrarySyncState(PhotoAccess.FULL, SyncStatus.Failed, PREVIEW_COUNT, null))
}
