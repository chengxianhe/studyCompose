package com.study.cc.data.di

import com.study.cc.domain.repository.ResearchSignalRepository
import com.study.cc.domain.usecase.GetHomeSummaryUseCase
import com.study.cc.domain.usecase.GetResearchSignalsUseCase
import com.study.cc.domain.usecase.RefreshResearchSignalsUseCase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
internal object ResearchSignalUseCaseModule {
    @Provides
    fun provideGetHomeSummaryUseCase(repository: ResearchSignalRepository): GetHomeSummaryUseCase =
        GetHomeSummaryUseCase(repository)

    @Provides
    fun provideGetResearchSignalsUseCase(repository: ResearchSignalRepository): GetResearchSignalsUseCase =
        GetResearchSignalsUseCase(repository)

    @Provides
    fun provideRefreshResearchSignalsUseCase(repository: ResearchSignalRepository): RefreshResearchSignalsUseCase =
        RefreshResearchSignalsUseCase(repository)
}
