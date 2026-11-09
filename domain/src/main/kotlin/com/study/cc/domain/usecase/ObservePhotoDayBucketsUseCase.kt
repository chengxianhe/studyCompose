package com.study.cc.domain.usecase

import com.study.cc.domain.model.PhotoDayBucket
import com.study.cc.domain.model.PhotoScope
import com.study.cc.domain.repository.PhotoTimelineRepository
import kotlinx.coroutines.flow.Flow

class ObservePhotoDayBucketsUseCase(private val repository: PhotoTimelineRepository) {
    operator fun invoke(scope: PhotoScope): Flow<List<PhotoDayBucket>> = repository.observeDayBuckets(scope)
}
