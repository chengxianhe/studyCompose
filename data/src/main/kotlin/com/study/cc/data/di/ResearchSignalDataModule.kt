package com.study.cc.data.di

import com.study.cc.data.repository.InMemoryResearchSignalRepository
import com.study.cc.domain.repository.ResearchSignalRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
internal abstract class ResearchSignalDataModule {
    @Binds
    abstract fun bindResearchSignalRepository(impl: InMemoryResearchSignalRepository): ResearchSignalRepository
}
