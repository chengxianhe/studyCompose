package com.study.cc.domain.repository

import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoDayBucket
import com.study.cc.domain.model.PhotoMedia
import com.study.cc.domain.model.PhotoScope
import kotlinx.coroutines.flow.Flow

interface PhotoTimelineRepository {
    fun observeDayBuckets(scope: PhotoScope): Flow<List<PhotoDayBucket>>

    suspend fun itemsOfDay(scope: PhotoScope, day: PhotoDay): List<PhotoMedia>
}
