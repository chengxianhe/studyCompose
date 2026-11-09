package com.study.cc.data.sync

import com.study.cc.data.store.MediaItemEntity
import com.study.cc.domain.usecase.ResolvePhotoDayUseCase
import java.time.ZoneId

/**
 * Converts taken time to a local date in the device zone. Falls back to the modified time, then to the unknown
 * bucket (0,0,0).
 */
class LocalDateCalculator(private val zone: ZoneId) {
    private val resolvePhotoDay = ResolvePhotoDayUseCase()

    fun effectiveTakenAtMs(row: MediaRow): Long =
        resolvePhotoDay(row.takenAtMs, row.dateModifiedSec, zone).effectiveTakenAtMs

    fun toEntity(row: MediaRow): MediaItemEntity {
        val resolution = resolvePhotoDay(row.takenAtMs, row.dateModifiedSec, zone)
        return MediaItemEntity(
            mediaStoreId = row.mediaStoreId,
            takenAtUtcMs = resolution.effectiveTakenAtMs,
            localYear = resolution.day.year,
            localMonth = resolution.day.month,
            localDay = resolution.day.day,
            mediaType = row.mediaType,
            bucketId = row.bucketId,
            dateModifiedSec = row.dateModifiedSec,
            generationModified = row.generationModified,
        )
    }
}
