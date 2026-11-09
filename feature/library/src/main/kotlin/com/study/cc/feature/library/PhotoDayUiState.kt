package com.study.cc.feature.library

import com.study.cc.domain.model.LibrarySyncState
import com.study.cc.domain.model.PhotoAccess
import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoDayBucket
import com.study.cc.domain.model.PhotoMedia
import com.study.cc.domain.model.SyncStatus

data class PhotoDayUiState(
    val library: LibrarySyncState = LibrarySyncState(PhotoAccess.NONE, SyncStatus.Idle, 0, null),
    val buckets: List<PhotoDayBucket> = emptyList(),
    val bucketsLoaded: Boolean = false,
    val itemsByDay: Map<PhotoDay, List<PhotoMedia>> = emptyMap(),
    val loadingDays: Set<PhotoDay> = emptySet(),
    val bucketLoadFailed: Boolean = false,
    val itemLoadFailed: Boolean = false,
) {
    val loadFailed: Boolean get() = bucketLoadFailed || itemLoadFailed
}
