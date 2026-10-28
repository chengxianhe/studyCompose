package com.study.cc.domain.usecase

import com.study.cc.domain.model.LibrarySyncState
import com.study.cc.domain.repository.MediaLibraryRepository
import kotlinx.coroutines.flow.Flow

class ObserveLibrarySyncStateUseCase(private val repository: MediaLibraryRepository) {
    operator fun invoke(): Flow<LibrarySyncState> = repository.observeSyncState()
}
