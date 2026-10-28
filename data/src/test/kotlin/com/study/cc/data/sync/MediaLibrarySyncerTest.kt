package com.study.cc.data.sync

import com.google.common.truth.Truth.assertThat
import com.study.cc.data.store.DayBucket
import com.study.cc.data.store.MediaLibraryDatabase
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import java.time.ZoneId

private const val MANY_DAYS = 2500
private const val BATCHES_SPAN = 25_000
private const val UNKNOWN_ID = 9L
private const val THIRD_ID = 3L
private const val THREE_ITEMS = 3

@RunWith(RobolectricTestRunner::class)
class MediaLibrarySyncerTest {
    private lateinit var database: MediaLibraryDatabase
    private val source = FakeMediaSource()
    private lateinit var syncer: MediaLibrarySyncer

    @Before
    fun setUp() {
        database = newDatabase(RuntimeEnvironment.getApplication())
        syncer = MediaLibrarySyncer(database, source, { ZoneId.of("UTC") }, fixedClock())
    }

    @After
    fun tearDown() = database.close()

    private fun buckets() = database.daySummaryDao().dayBuckets()

    @Test
    fun firstSyncInsertsEverythingAndBuildsSummaries() = runTest {
        source.put(row(1, taken(0)))
        source.put(row(2, taken(0, offsetMs = 1000)))
        source.put(row(THIRD_ID, taken(1)))

        val report = syncer.sync()

        assertThat(report.mode).isEqualTo(SyncMode.FULL)
        assertThat(report.counts.inserted).isEqualTo(THREE_ITEMS)
        assertThat(buckets()).containsExactly(
            DayBucket(YEAR, MONTH, DAY_28, 2),
            DayBucket(YEAR, MONTH, DAY_27, 1),
        ).inOrder()
    }

    @Test
    fun coverIsTheLatestItemOfTheDay() = runTest {
        source.put(row(1, taken(0, offsetMs = 5000)))
        source.put(row(2, taken(0, offsetMs = 9000)))
        source.put(row(THIRD_ID, taken(0)))

        syncer.sync()

        val day = database.daySummaryDao().daySummaries(YEAR, MONTH).single()
        assertThat(day.coverId).isEqualTo(2L)
        assertThat(day.latestTakenAt).isEqualTo(taken(0, offsetMs = 9000))
    }

    @Test
    fun missingTakenTimeFallsBackToModifiedTimeThenUnknownBucket() = runTest {
        source.put(row(1, takenAtMs = 0L, modifiedSec = taken(1) / 1000))
        source.put(row(UNKNOWN_ID, takenAtMs = 0L, modifiedSec = 0L))

        syncer.sync()

        assertThat(buckets()).containsExactly(
            DayBucket(YEAR, MONTH, DAY_27, 1),
            DayBucket(0, 0, 0, 1),
        ).inOrder()
    }

    @Test
    fun itemsSpanningSeveralBatchesAreAllImported() = runTest {
        for (id in 1L..BATCHES_SPAN) source.put(row(id * 2, taken(0, offsetMs = id)))

        val report = syncer.sync()

        assertThat(report.counts.inserted).isEqualTo(BATCHES_SPAN.toInt())
        assertThat(database.mediaItemDao().count()).isEqualTo(BATCHES_SPAN.toInt())
        assertThat(buckets().single().total).isEqualTo(BATCHES_SPAN.toInt())
    }

    @Test
    fun manyAffectedDaysRebuildTheWholeSummaryTable() = runTest {
        for (id in 1L..MANY_DAYS) source.put(row(id, taken(id.toInt())))

        syncer.sync()

        assertThat(database.daySummaryDao().count()).isEqualTo(MANY_DAYS)
        assertThat(database.dirtyDayDao().count()).isEqualTo(0)
    }

    @Test
    fun syncWithoutChangesIsIncrementalAndWritesNothing() = runTest {
        source.put(row(1, taken(0)))
        syncer.sync()

        val report = syncer.sync()

        assertThat(report.mode).isEqualTo(SyncMode.INCREMENTAL)
        assertThat(report.counts).isEqualTo(SyncCounts())
    }
}
