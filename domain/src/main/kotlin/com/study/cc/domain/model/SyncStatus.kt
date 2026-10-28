package com.study.cc.domain.model

sealed interface SyncStatus {
    data object Idle : SyncStatus

    /** `total` 为 null 表示总数未知。 */
    data class Syncing(val processed: Int, val total: Int?) : SyncStatus

    data object Failed : SyncStatus
}
