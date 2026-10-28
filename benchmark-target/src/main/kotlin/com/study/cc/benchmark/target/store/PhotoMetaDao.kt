package com.study.cc.benchmark.target.store

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface PhotoMetaDao {
    @Query("SELECT COUNT(*) FROM photo_meta")
    fun count(): Int

    @Query("SELECT COUNT(*) FROM photo_meta WHERE localYear = 0")
    fun unknownDateCount(): Int

    @Query(
        "SELECT localYear AS period, COUNT(*) AS total, id AS coverId, MAX(takenAtUtcMs) AS latestTakenAt " +
            "FROM photo_meta WHERE localYear > 0 GROUP BY localYear ORDER BY localYear DESC",
    )
    fun yearSummaries(): List<PeriodSummary>

    @Query(
        "SELECT localMonth AS period, COUNT(*) AS total, id AS coverId, MAX(takenAtUtcMs) AS latestTakenAt " +
            "FROM photo_meta WHERE localYear = :year GROUP BY localMonth ORDER BY localMonth DESC",
    )
    fun monthSummaries(year: Int): List<PeriodSummary>

    @Query(
        "SELECT localDay AS period, COUNT(*) AS total, id AS coverId, MAX(takenAtUtcMs) AS latestTakenAt " +
            "FROM photo_meta WHERE localYear = :year AND localMonth = :month GROUP BY localDay ORDER BY localDay DESC",
    )
    fun daySummaries(year: Int, month: Int): List<PeriodSummary>

    @Query(
        "SELECT id FROM photo_meta WHERE localYear = :year AND localMonth = :month AND localDay = :day " +
            "ORDER BY takenAtUtcMs DESC",
    )
    fun idsOfDay(year: Int, month: Int, day: Int): List<Long>

    /** 历史上的今天：按「月-日」字面匹配，`period` 是年份。 */
    @Query(
        "SELECT localYear AS period, COUNT(*) AS total, id AS coverId, MAX(takenAtUtcMs) AS latestTakenAt " +
            "FROM photo_meta WHERE localMonth = :month AND localDay = :day AND localYear > 0 " +
            "GROUP BY localYear ORDER BY localYear DESC",
    )
    fun onThisDay(month: Int, day: Int): List<PeriodSummary>

    /** 日流的全部桶（滑块与布局用）；未知日期桶因 year = 0 排在最后。 */
    @Query(
        "SELECT localYear AS year, localMonth AS month, localDay AS day, COUNT(*) AS total FROM photo_meta " +
            "GROUP BY localYear, localMonth, localDay ORDER BY localYear DESC, localMonth DESC, localDay DESC",
    )
    fun dayBuckets(): List<DayBucket>

    /** 对照：不预存本地日列，每行现算 `strftime(..., 'localtime')`。 */
    @Query(
        "SELECT CAST(strftime('%Y', takenAtUtcMs / 1000, 'unixepoch', 'localtime') AS INTEGER) AS period, " +
            "COUNT(*) AS total, id AS coverId, MAX(takenAtUtcMs) AS latestTakenAt " +
            "FROM photo_meta WHERE takenAtUtcMs > 0 GROUP BY period ORDER BY period DESC",
    )
    fun yearSummariesViaStrftime(): List<PeriodSummary>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    fun upsertAll(rows: List<PhotoMetaEntity>)
}
