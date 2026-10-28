package com.study.cc.data.store

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface DirtyDayDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    fun insertAll(days: List<DirtyDayEntity>)

    @Query("SELECT * FROM dirty_day")
    fun all(): List<DirtyDayEntity>

    @Query("SELECT COUNT(*) FROM dirty_day")
    fun count(): Int

    @Query("DELETE FROM dirty_day")
    fun clear()
}

@Dao
interface SyncStateDao {
    @Query("SELECT * FROM sync_state WHERE id = 1")
    fun get(): SyncStateEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    fun put(state: SyncStateEntity)
}
