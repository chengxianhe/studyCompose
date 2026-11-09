package com.study.cc.data.repository

import android.content.ContentUris
import android.provider.MediaStore
import com.study.cc.data.di.IoDispatcher
import com.study.cc.data.store.PhotoTimelineDao
import com.study.cc.data.sync.MEDIA_TYPE_VIDEO
import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoDayBucket
import com.study.cc.domain.model.PhotoMedia
import com.study.cc.domain.model.PhotoScope
import com.study.cc.domain.repository.PhotoTimelineRepository
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import javax.inject.Inject

internal class PhotoTimelineRepositoryImpl @Inject constructor(
    private val dao: PhotoTimelineDao,
    @IoDispatcher private val ioDispatcher: CoroutineDispatcher,
) : PhotoTimelineRepository {
    override fun observeDayBuckets(scope: PhotoScope): Flow<List<PhotoDayBucket>> {
        require(scope == PhotoScope.All)
        return dao.observeDayBuckets().map { rows ->
            rows.map { row -> PhotoDayBucket(PhotoDay(row.year, row.month, row.day), row.total) }
        }.flowOn(ioDispatcher)
    }

    override suspend fun itemsOfDay(scope: PhotoScope, day: PhotoDay): List<PhotoMedia> {
        require(scope == PhotoScope.All)
        return withContext(ioDispatcher) {
            dao.itemsOfDay(day.year, day.month, day.day).map { row ->
                val isVideo = row.mediaType == MEDIA_TYPE_VIDEO
                val baseUri = if (isVideo) {
                    MediaStore.Video.Media.EXTERNAL_CONTENT_URI
                } else {
                    MediaStore.Images.Media.EXTERNAL_CONTENT_URI
                }
                PhotoMedia(
                    id = row.mediaStoreId.toString(),
                    contentUri = ContentUris.withAppendedId(baseUri, row.mediaStoreId).toString(),
                    isVideo = isVideo,
                )
            }
        }
    }
}
