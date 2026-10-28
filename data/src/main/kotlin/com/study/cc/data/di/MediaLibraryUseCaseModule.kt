package com.study.cc.data.di

import com.study.cc.domain.repository.MediaLibraryRepository
import com.study.cc.domain.usecase.ObserveLibrarySyncStateUseCase
import com.study.cc.domain.usecase.RefreshMediaLibraryUseCase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
internal object MediaLibraryUseCaseModule {
    @Provides
    fun provideObserveLibrarySyncStateUseCase(repository: MediaLibraryRepository): ObserveLibrarySyncStateUseCase =
        ObserveLibrarySyncStateUseCase(repository)

    @Provides
    fun provideRefreshMediaLibraryUseCase(repository: MediaLibraryRepository): RefreshMediaLibraryUseCase =
        RefreshMediaLibraryUseCase(repository)
}
