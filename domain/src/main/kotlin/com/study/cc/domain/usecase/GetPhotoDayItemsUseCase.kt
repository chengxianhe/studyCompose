package com.study.cc.domain.usecase

import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoMedia
import com.study.cc.domain.model.PhotoScope
import com.study.cc.domain.repository.PhotoTimelineRepository

class GetPhotoDayItemsUseCase(private val repository: PhotoTimelineRepository) {
    suspend operator fun invoke(scope: PhotoScope, day: PhotoDay): List<PhotoMedia> = repository.itemsOfDay(scope, day)
}
