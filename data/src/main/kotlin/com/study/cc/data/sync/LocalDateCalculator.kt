package com.study.cc.data.sync

import com.study.cc.data.store.MediaItemEntity
import java.time.Instant
import java.time.ZoneId

private const val MS_PER_SECOND = 1000L

/**
 * Converts taken time to a local date in the device zone. Falls back to the modified time, then to the unknown
 * bucket (0,0,0).
 */
class LocalDateCalculator(private val zone: ZoneId) {
    fun effectiveTakenAtMs(row: MediaRow): Long = when {
        row.takenAtMs > 0 -> row.takenAtMs
        row.dateModifiedSec > 0 -> row.dateModifiedSec * MS_PER_SECOND
        else -> 0L
    }

    fun toEntity(row: MediaRow): MediaItemEntity {
        val takenAt = effectiveTakenAtMs(row)
        val date = if (takenAt > 0) Instant.ofEpochMilli(takenAt).atZone(zone).toLocalDate() else null
        return MediaItemEntity(
            mediaStoreId = row.mediaStoreId,
            takenAtUtcMs = takenAt,
            localYear = date?.year ?: 0,
            localMonth = date?.monthValue ?: 0,
            localDay = date?.dayOfMonth ?: 0,
            mediaType = row.mediaType,
            bucketId = row.bucketId,
            dateModifiedSec = row.dateModifiedSec,
            generationModified = row.generationModified,
        )
    }
}
