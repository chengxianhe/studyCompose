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

private const val LATE_HOUR_MS = 11L * 3_600_000L + 30L * 60_000L
private const val SHANGHAI = "Asia/Shanghai"
private const val DAY_29 = 29

@RunWith(RobolectricTestRunner::class)
class MediaLibraryIncrementalSyncTest {
    private lateinit var database: MediaLibraryDatabase
    private val source = FakeMediaSource()
    private var zone = ZoneId.of("UTC")
    private lateinit var syncer: MediaLibrarySyncer

    @Before
    fun setUp() {
        database = newDatabase(RuntimeEnvironment.getApplication())
        syncer = MediaLibrarySyncer(database, source, { zone }, fixedClock())
    }

    @After
    fun tearDown() = database.close()

    private fun buckets() = database.daySummaryDao().dayBuckets()

    @Test
    fun incrementalAddsNewItemsToTheirDay() = runTest {
        source.put(row(1, taken(0)))
        syncer.sync()
        source.put(row(2, taken(0, offsetMs = 1000)))

        val report = syncer.sync()

        assertThat(report.mode).isEqualTo(SyncMode.INCREMENTAL)
        assertThat(report.counts.inserted).isEqualTo(1)
        assertThat(buckets()).containsExactly(DayBucket(YEAR, MONTH, DAY_28, 2))
    }

    @Test
    fun changingTheDateMovesTheItemBetweenDays() = runTest {
        source.put(row(1, taken(0)))
        source.put(row(2, taken(1)))
        syncer.sync()
        source.put(row(1, taken(1, offsetMs = 1000), modifiedSec = taken(0) / 1000 + 1))

        val report = syncer.sync()

        assertThat(report.counts.updated).isEqualTo(1)
        assertThat(buckets()).containsExactly(DayBucket(YEAR, MONTH, DAY_27, 2))
    }

    @Test
    fun deletionsAreFoundWhenTheCountsDisagree() = runTest {
        source.put(row(1, taken(0)))
        source.put(row(2, taken(1)))
        syncer.sync()
        source.remove(2)

        val report = syncer.sync()

        assertThat(report.counts.deleted).isEqualTo(1)
        assertThat(database.mediaItemDao().count()).isEqualTo(1)
        assertThat(buckets()).containsExactly(DayBucket(YEAR, MONTH, DAY_28, 1))
    }

    @Test
    fun removingEverythingEmptiesTheLibrary() = runTest {
        source.put(row(1, taken(0)))
        source.put(row(2, taken(1)))
        syncer.sync()
        source.remove(1)
        source.remove(2)

        syncer.sync()

        assertThat(database.mediaItemDao().count()).isEqualTo(0)
        assertThat(buckets()).isEmpty()
    }

    @Test
    fun versionChangeForcesAFullReconcile() = runTest {
        source.put(row(1, taken(0)))
        syncer.sync()
        source.version = "v2"

        assertThat(syncer.sync().mode).isEqualTo(SyncMode.FULL)
    }

    @Test
    fun timeZoneChangeRecomputesLocalDates() = runTest {
        source.put(row(1, taken(0, offsetMs = LATE_HOUR_MS)))
        syncer.sync()
        assertThat(buckets()).containsExactly(DayBucket(YEAR, MONTH, DAY_28, 1))
        zone = ZoneId.of(SHANGHAI)

        val report = syncer.sync()

        assertThat(report.mode).isEqualTo(SyncMode.ZONE_REBUILD)
        assertThat(buckets()).containsExactly(DayBucket(YEAR, MONTH, DAY_29, 1))
    }

    @Test
    fun withoutGenerationSupportChangesAreFoundByModifiedTime() = runTest {
        source.supportsGeneration = false
        source.put(row(1, taken(1)))
        syncer.sync()
        source.put(row(2, taken(0), modifiedSec = fixedClock().millis() / 1000 + 1))

        val report = syncer.sync()

        assertThat(report.counts.inserted).isEqualTo(1)
        assertThat(buckets()).hasSize(2)
    }
}
