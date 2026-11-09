package com.study.cc.data.di

import com.study.cc.data.repository.PhotoTimelineRepositoryImpl
import com.study.cc.data.store.MediaLibraryDatabase
import com.study.cc.data.store.PhotoTimelineDao
import com.study.cc.domain.repository.PhotoTimelineRepository
import com.study.cc.domain.usecase.GetPhotoDayItemsUseCase
import com.study.cc.domain.usecase.ObservePhotoDayBucketsUseCase
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers

@Module
@InstallIn(SingletonComponent::class)
internal abstract class PhotoTimelineModule {
    @Binds
    abstract fun bindPhotoTimelineRepository(impl: PhotoTimelineRepositoryImpl): PhotoTimelineRepository

    companion object {
        @Provides
        fun providePhotoTimelineDao(database: MediaLibraryDatabase): PhotoTimelineDao = database.photoTimelineDao()

        @Provides
        @IoDispatcher
        fun provideIoDispatcher(): CoroutineDispatcher = Dispatchers.IO

        @Provides
        fun provideObservePhotoDayBucketsUseCase(repository: PhotoTimelineRepository): ObservePhotoDayBucketsUseCase =
            ObservePhotoDayBucketsUseCase(repository)

        @Provides
        fun provideGetPhotoDayItemsUseCase(repository: PhotoTimelineRepository): GetPhotoDayItemsUseCase =
            GetPhotoDayItemsUseCase(repository)
    }
}
