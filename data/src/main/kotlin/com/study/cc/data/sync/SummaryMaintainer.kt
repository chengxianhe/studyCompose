package com.study.cc.data.sync

import com.study.cc.data.store.MediaLibraryDatabase

private const val REBUILD_ALL_THRESHOLD = 2000

/** Recomputes summaries for the days in `dirty_day`: rebuilds the whole table when there are many, else day by day. */
internal class SummaryMaintainer(private val database: MediaLibraryDatabase) {
    private val summaries = database.daySummaryDao()
    private val dirtyDays = database.dirtyDayDao()

    fun refreshDirtyDays() {
        val dirty = dirtyDays.all()
        if (dirty.isEmpty()) return
        database.runInTransaction {
            if (dirty.size > REBUILD_ALL_THRESHOLD) {
                summaries.clear()
                summaries.rebuildAll()
            } else {
                dirty.forEach { day ->
                    summaries.deleteDay(day.localYear, day.localMonth, day.localDay)
                    summaries.rebuildDay(day.localYear, day.localMonth, day.localDay)
                }
            }
            dirtyDays.clear()
        }
    }
}
