package com.study.cc.data.store

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface DaySummaryDao {
    @Query("DELETE FROM day_summary WHERE localYear = :year AND localMonth = :month AND localDay = :day")
    fun deleteDay(year: Int, month: Int, day: Int)

    /** Recomputes one day from its current items; produces no row when the day is empty. */
    @Query(
        "INSERT OR REPLACE INTO day_summary " +
            "SELECT localYear, localMonth, localDay, COUNT(*), mediaStoreId, MAX(takenAtUtcMs) FROM media_item " +
            "WHERE localYear = :year AND localMonth = :month AND localDay = :day " +
            "GROUP BY localYear, localMonth, localDay",
    )
    fun rebuildDay(year: Int, month: Int, day: Int)

    @Query("DELETE FROM day_summary")
    fun clear()

    /** Rebuilds every day in one statement; much faster than per day when many days changed (e.g. first sync). */
    @Query(
        "INSERT INTO day_summary " +
            "SELECT localYear, localMonth, localDay, COUNT(*), mediaStoreId, MAX(takenAtUtcMs) FROM media_item " +
            "GROUP BY localYear, localMonth, localDay",
    )
    fun rebuildAll()

    @Query("SELECT COUNT(*) FROM day_summary")
    fun count(): Int

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    fun upsert(rows: List<DaySummaryEntity>)

    @Query(
        "SELECT localYear AS period, SUM(total) AS total, coverId, MAX(latestTakenAt) AS latestTakenAt " +
            "FROM day_summary WHERE localYear > 0 GROUP BY localYear ORDER BY localYear DESC",
    )
    fun yearSummaries(): List<PeriodSummary>

    @Query(
        "SELECT localMonth AS period, SUM(total) AS total, coverId, MAX(latestTakenAt) AS latestTakenAt " +
            "FROM day_summary WHERE localYear = :year GROUP BY localMonth ORDER BY localMonth DESC",
    )
    fun monthSummaries(year: Int): List<PeriodSummary>

    @Query(
        "SELECT localDay AS period, total, coverId, latestTakenAt FROM day_summary " +
            "WHERE localYear = :year AND localMonth = :month ORDER BY localDay DESC",
    )
    fun daySummaries(year: Int, month: Int): List<PeriodSummary>

    /** Every bucket of the day stream; the unknown-date bucket sorts last because its year is 0. */
    @Query(
        "SELECT localYear AS year, localMonth AS month, localDay AS day, total FROM day_summary " +
            "ORDER BY localYear DESC, localMonth DESC, localDay DESC",
    )
    fun dayBuckets(): List<DayBucket>

    /** On this day: literal month-day match; `period` is the year. */
    @Query(
        "SELECT localYear AS period, total, coverId, latestTakenAt FROM day_summary " +
            "WHERE localMonth = :month AND localDay = :day AND localYear > 0 ORDER BY localYear DESC",
    )
    fun onThisDay(month: Int, day: Int): List<PeriodSummary>
}
