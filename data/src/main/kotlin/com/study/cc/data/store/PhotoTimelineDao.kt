package com.study.cc.data.store

import androidx.room.Dao
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

data class TimelineDayRow(val year: Int, val month: Int, val day: Int, val total: Int)

data class TimelineMediaRow(val mediaStoreId: Long, val mediaType: Int)

@Dao
interface PhotoTimelineDao {
    /** The small day summary table drives both the stream and its date scrubber. */
    @Query(
        "SELECT localYear AS year, localMonth AS month, localDay AS day, total FROM day_summary " +
            "ORDER BY localYear DESC, localMonth DESC, localDay DESC",
    )
    fun observeDayBuckets(): Flow<List<TimelineDayRow>>

    /** A day is the largest result the UI may request; no query reads the complete library. */
    @Query(
        "SELECT mediaStoreId, mediaType FROM media_item " +
            "WHERE localYear = :year AND localMonth = :month AND localDay = :day " +
            "ORDER BY takenAtUtcMs DESC, mediaStoreId DESC",
    )
    suspend fun itemsOfDay(year: Int, month: Int, day: Int): List<TimelineMediaRow>
}
