package com.study.cc.domain.model

data class LibrarySyncState(
    val access: PhotoAccess,
    val status: SyncStatus,
    val itemCount: Int,
    val lastSyncAtMs: Long?,
)
