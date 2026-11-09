package com.study.cc.data.repository

import com.google.common.truth.Truth.assertThat
import com.study.cc.data.store.DaySummaryEntity
import com.study.cc.data.store.MediaItemEntity
import com.study.cc.data.sync.MEDIA_TYPE_IMAGE
import com.study.cc.data.sync.MEDIA_TYPE_VIDEO
import com.study.cc.data.sync.newDatabase
import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment

private const val YEAR = 2026
private const val MONTH = 10
private const val OLDER_DAY = 28
private const val NEWER_DAY = 29
private const val VIDEO_ID = 3L
private const val MS_PER_SECOND = 1000L

@RunWith(RobolectricTestRunner::class)
class PhotoTimelineRepositoryTest {
    private val database = newDatabase(RuntimeEnvironment.getApplication())
    private val repository = PhotoTimelineRepositoryImpl(database.photoTimelineDao(), Dispatchers.IO)

    @After
    fun close() = database.close()

    @Test
    fun dayBucketsSortUnknownDateLast() = runTest {
        database.daySummaryDao().upsert(
            listOf(
                DaySummaryEntity(0, 0, 0, 1, 1, 0),
                DaySummaryEntity(YEAR, MONTH, OLDER_DAY, 2, 2, 0),
                DaySummaryEntity(YEAR, MONTH, NEWER_DAY, 1, VIDEO_ID, 0),
            ),
        )

        val buckets = repository.observeDayBuckets(PhotoScope.All).first()

        assertThat(buckets.map { it.day })
            .containsExactly(PhotoDay(YEAR, MONTH, NEWER_DAY), PhotoDay(YEAR, MONTH, OLDER_DAY), PhotoDay.Unknown)
            .inOrder()
    }

    @Test
    fun queryingOneDayReturnsOnlyItsItemsAndMediaUris() = runTest {
        database.mediaItemDao().upsertAll(
            listOf(
                item(1, YEAR, MONTH, OLDER_DAY, MEDIA_TYPE_IMAGE),
                item(2, YEAR, MONTH, NEWER_DAY, MEDIA_TYPE_IMAGE),
                item(VIDEO_ID, YEAR, MONTH, NEWER_DAY, MEDIA_TYPE_VIDEO),
            ),
        )

        val items = repository.itemsOfDay(PhotoScope.All, PhotoDay(YEAR, MONTH, NEWER_DAY))

        assertThat(items.map { it.id }).containsExactly("3", "2").inOrder()
        assertThat(items.map { it.isVideo }).containsExactly(true, false).inOrder()
        assertThat(items[0].contentUri).contains("/video/media/3")
        assertThat(items[1].contentUri).contains("/images/media/2")
    }

    private fun item(id: Long, year: Int, month: Int, day: Int, mediaType: Int) = MediaItemEntity(
        mediaStoreId = id,
        takenAtUtcMs = id * MS_PER_SECOND,
        localYear = year,
        localMonth = month,
        localDay = day,
        mediaType = mediaType,
        bucketId = 1,
        dateModifiedSec = id,
        generationModified = 1,
    )
}
