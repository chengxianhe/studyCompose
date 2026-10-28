package com.study.cc.data.sync

import com.study.cc.data.store.DirtyDayEntity
import com.study.cc.data.store.ItemStamp
import com.study.cc.data.store.MediaLibraryDatabase

private const val IN_CHUNK = 500

data class SyncCounts(val inserted: Int = 0, val updated: Int = 0, val deleted: Int = 0) {
    operator fun plus(other: SyncCounts) =
        SyncCounts(inserted + other.inserted, updated + other.updated, deleted + other.deleted)
}

/**
 * Writes one batch and records affected days in `dirty_day`; summaries are recomputed once per sync.
 * The caller owns the transaction.
 */
internal class BatchApplier(database: MediaLibraryDatabase, private val calculator: LocalDateCalculator) {
    private val items = database.mediaItemDao()
    private val dirtyDays = database.dirtyDayDao()

    fun existingByIds(ids: List<Long>): Map<Long, ItemStamp> =
        ids.chunked(IN_CHUNK).flatMap { items.stampsByIds(it) }.associateBy { it.mediaStoreId }

    fun existingInRange(low: Long, high: Long): Map<Long, ItemStamp> =
        items.stampsInRange(low, high).associateBy { it.mediaStoreId }

    /** Writes new or changed rows; `forceUpdate` recomputes local dates after a time zone change. */
    fun upsert(rows: List<MediaRow>, existing: Map<Long, ItemStamp>, forceUpdate: Boolean): SyncCounts {
        val entities = ArrayList<com.study.cc.data.store.MediaItemEntity>()
        val dirty = HashSet<DirtyDayEntity>()
        var inserted = 0
        var updated = 0
        for (row in rows) {
            val old = existing[row.mediaStoreId]
            if (old != null && !forceUpdate && old.dateModifiedSec == row.dateModifiedSec) continue
            val entity = calculator.toEntity(row)
            entities += entity
            dirty += DirtyDayEntity(entity.localYear, entity.localMonth, entity.localDay)
            if (old == null) {
                inserted++
            } else {
                updated++
                dirty += old.toDirtyDay()
            }
        }
        dirtyDays.insertAll(dirty.toList())
        items.upsertAll(entities)
        return SyncCounts(inserted = inserted, updated = updated)
    }

    fun delete(stamps: Collection<ItemStamp>): SyncCounts {
        if (stamps.isEmpty()) return SyncCounts()
        dirtyDays.insertAll(stamps.map { it.toDirtyDay() }.distinct())
        stamps.map { it.mediaStoreId }.chunked(IN_CHUNK).forEach { items.deleteByIds(it) }
        return SyncCounts(deleted = stamps.size)
    }

    /** The source has nothing after `lastId`, so everything left in the database after it is deleted. */
    fun deleteAfter(lastId: Long): SyncCounts {
        if (!items.anyAfter(lastId)) return SyncCounts()
        val before = items.count()
        items.markDirtyAfter(lastId)
        items.deleteAfter(lastId)
        return SyncCounts(deleted = before - items.count())
    }

    private fun ItemStamp.toDirtyDay() = DirtyDayEntity(localYear, localMonth, localDay)
}
