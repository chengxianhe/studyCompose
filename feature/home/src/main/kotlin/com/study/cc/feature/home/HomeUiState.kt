package com.study.cc.feature.home

import com.study.cc.domain.model.LibrarySyncState
import com.study.cc.domain.model.PhotoAccess
import com.study.cc.domain.model.SyncStatus

data class HomeUiState(
    val library: LibrarySyncState = LibrarySyncState(
        access = PhotoAccess.NONE,
        status = SyncStatus.Idle,
        itemCount = 0,
        lastSyncAtMs = null,
    ),
)
