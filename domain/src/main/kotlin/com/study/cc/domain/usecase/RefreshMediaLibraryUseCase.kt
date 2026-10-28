package com.study.cc.domain.usecase

import com.study.cc.domain.repository.MediaLibraryRepository

class RefreshMediaLibraryUseCase(private val repository: MediaLibraryRepository) {
    suspend operator fun invoke() = repository.refresh()
}
