package com.study.cc.feature.library

import com.google.common.truth.Truth.assertThat
import com.study.cc.core.logging.Logger
import com.study.cc.domain.model.LibrarySyncState
import com.study.cc.domain.model.PhotoAccess
import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoDayBucket
import com.study.cc.domain.model.PhotoMedia
import com.study.cc.domain.model.PhotoScope
import com.study.cc.domain.model.SyncStatus
import com.study.cc.domain.repository.MediaLibraryRepository
import com.study.cc.domain.repository.PhotoTimelineRepository
import com.study.cc.domain.usecase.GetPhotoDayItemsUseCase
import com.study.cc.domain.usecase.ObserveLibrarySyncStateUseCase
import com.study.cc.domain.usecase.ObservePhotoDayBucketsUseCase
import com.study.cc.domain.usecase.RefreshMediaLibraryUseCase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test

private const val DAY_COUNT = 13
private const val CACHE_LIMIT = 12
private const val YEAR = 2026
private const val MONTH = 10
private const val DAY = 29

private class FakeTimelineRepository : PhotoTimelineRepository {
    val buckets = MutableStateFlow<List<PhotoDayBucket>>(emptyList())
    val requestedDays = mutableListOf<PhotoDay>()

    override fun observeDayBuckets(scope: PhotoScope): Flow<List<PhotoDayBucket>> = buckets

    override suspend fun itemsOfDay(scope: PhotoScope, day: PhotoDay): List<PhotoMedia> {
        requestedDays += day
        return listOf(PhotoMedia(day.day.toString(), "content://photo/${day.day}", false))
    }
}

private class FakeSyncRepository : MediaLibraryRepository {
    val state = MutableStateFlow(LibrarySyncState(PhotoAccess.FULL, SyncStatus.Idle, DAY_COUNT, null))

    override fun observeSyncState(): Flow<LibrarySyncState> = state

    override suspend fun refresh() = Unit
}

private object NoOpLogger : Logger {
    override fun d(tag: String, message: String) = Unit

    override fun i(tag: String, message: String) = Unit

    override fun w(tag: String, message: String, throwable: Throwable?) = Unit

    override fun e(tag: String, message: String, throwable: Throwable?) = Unit
}

@OptIn(ExperimentalCoroutinesApi::class)
class PhotoDayViewModelTest {
    private val timeline = FakeTimelineRepository()
    private val sync = FakeSyncRepository()

    @Before
    fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())

    @After
    fun tearDown() = Dispatchers.resetMain()

    @Test
    fun loadsOnlyRequestedDaysAndKeepsARecentBoundedCache() = runTest {
        val days = (1..DAY_COUNT).map { PhotoDay(YEAR, MONTH, it) }
        timeline.buckets.value = days.map { PhotoDayBucket(it, 1) }
        val viewModel = viewModel()

        days.forEach { viewModel.onVisibleDaysChanged(setOf(it)) }

        assertThat(timeline.requestedDays).containsExactlyElementsIn(days).inOrder()
        assertThat(viewModel.uiState.value.itemsByDay).hasSize(CACHE_LIMIT)
        assertThat(viewModel.uiState.value.itemsByDay).doesNotContainKey(days.first())
    }

    @Test
    fun daySummaryChangeInvalidatesLoadedItems() = runTest {
        val day = PhotoDay(YEAR, MONTH, DAY)
        timeline.buckets.value = listOf(PhotoDayBucket(day, 1))
        val viewModel = viewModel()
        viewModel.onVisibleDaysChanged(setOf(day))
        assertThat(viewModel.uiState.value.itemsByDay).containsKey(day)

        timeline.buckets.value = listOf(PhotoDayBucket(day, 2))

        assertThat(timeline.requestedDays).containsExactly(day, day)
        assertThat(viewModel.uiState.value.itemsByDay).containsKey(day)
        assertThat(viewModel.uiState.value.buckets.single().total).isEqualTo(2)
    }

    private fun viewModel() = PhotoDayViewModel(
        ObserveLibrarySyncStateUseCase(sync),
        ObservePhotoDayBucketsUseCase(timeline),
        GetPhotoDayItemsUseCase(timeline),
        RefreshMediaLibraryUseCase(sync),
        NoOpLogger,
    )
}
