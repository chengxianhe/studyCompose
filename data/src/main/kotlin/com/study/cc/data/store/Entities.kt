package com.study.cc.data.store

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Lightweight metadata without paths or locations. `takenAtUtcMs == 0` with `localYear == 0` means unknown date.
 * The first two indexes include `takenAtUtcMs` so day recomputation and "on this day" scan only the index (covering).
 */
@Entity(
    tableName = "media_item",
    indices = [
        Index(value = ["localYear", "localMonth", "localDay", "takenAtUtcMs"]),
        Index(value = ["localMonth", "localDay", "localYear", "takenAtUtcMs"]),
        Index(value = ["bucketId"]),
    ],
)
data class MediaItemEntity(
    @PrimaryKey val mediaStoreId: Long,
    val takenAtUtcMs: Long,
    val localYear: Int,
    val localMonth: Int,
    val localDay: Int,
    val mediaType: Int,
    val bucketId: Long,
    val dateModifiedSec: Long,
    val generationModified: Long,
)

/** One row per day that has items; `(0,0,0)` is the unknown-date bucket. Year and month summaries aggregate it. */
@Entity(tableName = "day_summary", primaryKeys = ["localYear", "localMonth", "localDay"])
data class DaySummaryEntity(
    val localYear: Int,
    val localMonth: Int,
    val localDay: Int,
    val total: Int,
    val coverId: Long,
    val latestTakenAt: Long,
)

/** Days whose summary must be recomputed; stored so a sync killed midway can still catch up. */
@Entity(tableName = "dirty_day", primaryKeys = ["localYear", "localMonth", "localDay"])
data class DirtyDayEntity(val localYear: Int, val localMonth: Int, val localDay: Int)

/** Single row (`id` is always 1). */
@Entity(tableName = "sync_state")
data class SyncStateEntity(
    @PrimaryKey val id: Int = SINGLE_ROW_ID,
    val lastGeneration: Long,
    val lastSyncSec: Long,
    val mediaStoreVersion: String,
    val zoneId: String,
    val lastSyncAtMs: Long,
) {
    companion object {
        const val SINGLE_ROW_ID = 1
    }
}
