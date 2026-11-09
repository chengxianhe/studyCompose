package com.study.cc.data.store

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [MediaItemEntity::class, DaySummaryEntity::class, DirtyDayEntity::class, SyncStateEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class MediaLibraryDatabase : RoomDatabase() {
    abstract fun mediaItemDao(): MediaItemDao

    abstract fun daySummaryDao(): DaySummaryDao

    abstract fun photoTimelineDao(): PhotoTimelineDao

    abstract fun dirtyDayDao(): DirtyDayDao

    abstract fun syncStateDao(): SyncStateDao

    companion object {
        const val FILE_NAME = "media_library.db"
    }
}
