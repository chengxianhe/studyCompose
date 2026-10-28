package com.study.cc.data.di

import android.content.Context
import androidx.room.Room
import com.study.cc.data.mediastore.MediaStoreSource
import com.study.cc.data.repository.MediaLibraryRepositoryImpl
import com.study.cc.data.store.MediaLibraryDatabase
import com.study.cc.data.sync.MediaLibrarySyncer
import com.study.cc.data.sync.MediaSource
import com.study.cc.domain.repository.MediaLibraryRepository
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import java.time.Clock
import java.time.ZoneId
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
internal abstract class MediaLibraryDataModule {
    @Binds
    abstract fun bindMediaLibraryRepository(impl: MediaLibraryRepositoryImpl): MediaLibraryRepository

    @Binds
    abstract fun bindMediaSource(impl: MediaStoreSource): MediaSource

    companion object {
        @Provides
        @Singleton
        fun provideDatabase(@ApplicationContext context: Context): MediaLibraryDatabase =
            Room.databaseBuilder(context, MediaLibraryDatabase::class.java, MediaLibraryDatabase.FILE_NAME).build()

        @Provides
        fun provideClock(): Clock = Clock.systemUTC()

        @Provides
        @Singleton
        @MediaSyncScope
        fun provideSyncScope(): CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

        @Provides
        @Singleton
        fun provideSyncer(database: MediaLibraryDatabase, source: MediaSource, clock: Clock): MediaLibrarySyncer =
            MediaLibrarySyncer(database, source, { ZoneId.systemDefault() }, clock)
    }
}
