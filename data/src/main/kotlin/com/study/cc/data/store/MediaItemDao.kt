package com.study.cc.data.store

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface MediaItemDao {
    @Query("SELECT COUNT(*) FROM media_item")
    fun count(): Int

    @Query("SELECT COUNT(*) FROM media_item WHERE localYear = 0")
    fun unknownDateCount(): Int

    @Query(
        "SELECT mediaStoreId, dateModifiedSec, localYear, localMonth, localDay FROM media_item " +
            "WHERE mediaStoreId BETWEEN :low AND :high",
    )
    fun stampsInRange(low: Long, high: Long): List<ItemStamp>

    @Query(
        "SELECT mediaStoreId, dateModifiedSec, localYear, localMonth, localDay FROM media_item " +
            "WHERE mediaStoreId IN (:ids)",
    )
    fun stampsByIds(ids: List<Long>): List<ItemStamp>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    fun upsertAll(rows: List<MediaItemEntity>)

    @Query("DELETE FROM media_item WHERE mediaStoreId IN (:ids)")
    fun deleteByIds(ids: List<Long>)

    @Query("DELETE FROM media_item WHERE mediaStoreId > :id")
    fun deleteAfter(id: Long)

    @Query(
        "INSERT OR IGNORE INTO dirty_day SELECT DISTINCT localYear, localMonth, localDay FROM media_item " +
            "WHERE mediaStoreId > :id",
    )
    fun markDirtyAfter(id: Long)

    @Query("SELECT EXISTS(SELECT 1 FROM media_item WHERE mediaStoreId > :id)")
    fun anyAfter(id: Long): Boolean

    @Query(
        "SELECT mediaStoreId FROM media_item WHERE localYear = :year AND localMonth = :month AND localDay = :day " +
            "ORDER BY takenAtUtcMs DESC",
    )
    fun idsOfDay(year: Int, month: Int, day: Int): List<Long>
}
