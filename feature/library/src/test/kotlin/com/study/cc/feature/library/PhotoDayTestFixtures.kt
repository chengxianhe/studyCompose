package com.study.cc.feature.library

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
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf

private const val YEAR = 2026
private const val MONTH = 10
private const val DAY = 29

internal val firstDay = PhotoDay(YEAR, MONTH, DAY)

internal class ControlledTimeline : PhotoTimelineRepository {
    var observe: () -> Flow<List<PhotoDayBucket>> = { flowOf(listOf(PhotoDayBucket(firstDay, 1))) }
    var query: suspend (PhotoDay) -> List<PhotoMedia> = { emptyList() }

    override fun observeDayBuckets(scope: PhotoScope) = observe()

    override suspend fun itemsOfDay(scope: PhotoScope, day: PhotoDay) = query(day)
}

internal object IdleLibrary : MediaLibraryRepository {
    override fun observeSyncState() = flowOf(LibrarySyncState(PhotoAccess.FULL, SyncStatus.Idle, 1, null))

    override suspend fun refresh() = Unit
}

internal object SilentLogger : Logger {
    override fun d(tag: String, message: String) = Unit

    override fun i(tag: String, message: String) = Unit

    override fun w(tag: String, message: String, throwable: Throwable?) = Unit

    override fun e(tag: String, message: String, throwable: Throwable?) = Unit
}
