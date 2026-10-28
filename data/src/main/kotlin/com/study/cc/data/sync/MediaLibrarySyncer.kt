package com.study.cc.data.sync

import com.study.cc.data.store.MediaLibraryDatabase
import com.study.cc.data.store.SyncStateEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.time.Clock
import java.time.ZoneId
import kotlin.coroutines.coroutineContext

private const val BATCH_SIZE = 10_000
private const val MODIFIED_SLACK_SEC = 60L
private const val MS_PER_SECOND = 1000L

enum class SyncMode { FULL, ZONE_REBUILD, INCREMENTAL }

data class SyncReport(val mode: SyncMode, val counts: SyncCounts, val startedAtMs: Long, val finishedAtMs: Long) {
    val durationMs: Long get() = finishedAtMs - startedAtMs
}

fun interface SyncProgressListener {
    fun onProgress(processed: Int, total: Int?)
}

/**
 * Syncs the system media library into Room: first run, version change or time zone change use a full ordered merge,
 * everything else is incremental, followed by a reconcile if the counts disagree (MediaStore reports no deletions).
 * Summaries are recomputed once at the end of each sync.
 */
class MediaLibrarySyncer(
    private val database: MediaLibraryDatabase,
    private val source: MediaSource,
    private val zoneProvider: () -> ZoneId,
    private val clock: Clock,
) {
    private val items = database.mediaItemDao()
    private val summaries = SummaryMaintainer(database)

    /** Number of items currently stored. */
    fun itemCount(): Int = items.count()

    suspend fun sync(listener: SyncProgressListener = SyncProgressListener { _, _ -> }): SyncReport =
        withContext(Dispatchers.IO) {
            val started = clock.millis()
            val state = database.syncStateDao().get()
            val zone = zoneProvider()
            val version = source.version()
            // Read the generation before scanning so changes made during the scan are picked up next time
            val generation = source.generation()
            val applier = BatchApplier(database, LocalDateCalculator(zone))
            val mode = chooseMode(state, version, zone)
            val counts =
                when (mode) {
                    SyncMode.FULL -> reconcile(applier, forceUpdate = false, listener)
                    SyncMode.ZONE_REBUILD -> reconcile(applier, forceUpdate = true, listener)
                    SyncMode.INCREMENTAL -> incremental(applier, checkNotNull(state), listener)
                }
            summaries.refreshDirtyDays()
            val now = clock.millis()
            database.syncStateDao().put(
                SyncStateEntity(
                    lastGeneration = generation,
                    lastSyncSec = started / MS_PER_SECOND,
                    mediaStoreVersion = version,
                    zoneId = zone.id,
                    lastSyncAtMs = now,
                ),
            )
            SyncReport(mode, counts, started, now)
        }

    private fun chooseMode(state: SyncStateEntity?, version: String, zone: ZoneId): SyncMode = when {
        state == null || state.mediaStoreVersion != version -> SyncMode.FULL
        state.zoneId != zone.id -> SyncMode.ZONE_REBUILD
        else -> SyncMode.INCREMENTAL
    }

    /** Merges the cursor with stored rows in `_ID` order: inserts missing, updates changed, deletes extra. */
    private suspend fun reconcile(
        applier: BatchApplier,
        forceUpdate: Boolean,
        listener: SyncProgressListener,
    ): SyncCounts {
        var counts = SyncCounts()
        var lastId = 0L
        var processed = 0
        val total = source.count()
        source.openAll().use { rows ->
            while (rows.hasNext()) {
                coroutineContext.ensureActive()
                val batch = rows.takeBatch()
                val low = lastId + 1
                val high = batch.last().mediaStoreId
                counts += database.runInTransaction<SyncCounts> {
                    val existing = applier.existingInRange(low, high)
                    val kept = batch.mapTo(HashSet()) { it.mediaStoreId }
                    applier.upsert(batch, existing, forceUpdate) +
                        applier.delete(existing.values.filter { it.mediaStoreId !in kept })
                }
                lastId = high
                processed += batch.size
                listener.onProgress(processed, total)
            }
        }
        return counts + database.runInTransaction<SyncCounts> { applier.deleteAfter(lastId) }
    }

    private suspend fun incremental(
        applier: BatchApplier,
        state: SyncStateEntity,
        listener: SyncProgressListener,
    ): SyncCounts {
        var counts = SyncCounts()
        var processed = 0
        source.openChanged(state.lastGeneration, state.lastSyncSec - MODIFIED_SLACK_SEC).use { rows ->
            while (rows.hasNext()) {
                coroutineContext.ensureActive()
                val batch = rows.takeBatch()
                counts += database.runInTransaction<SyncCounts> {
                    applier.upsert(batch, applier.existingByIds(batch.map { it.mediaStoreId }), forceUpdate = false)
                }
                processed += batch.size
                listener.onProgress(processed, null)
            }
        }
        // A count mismatch means deletions, which an incremental pass cannot see, so reconcile once
        return if (source.count() != items.count()) counts + reconcile(applier, false, listener) else counts
    }

    private fun MediaRows.takeBatch(): List<MediaRow> {
        val batch = ArrayList<MediaRow>(BATCH_SIZE)
        while (batch.size < BATCH_SIZE && hasNext()) batch += next()
        return batch
    }
}
