package com.study.cc.data.di

import com.study.cc.domain.repository.StockMarketRepository
import com.study.cc.domain.usecase.GetDailyBarsUseCase
import com.study.cc.domain.usecase.GetQuoteUseCase
import com.study.cc.domain.usecase.SearchSecuritiesUseCase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
internal object StockUseCaseModule {
    @Provides
    fun provideSearchSecuritiesUseCase(repository: StockMarketRepository): SearchSecuritiesUseCase =
        SearchSecuritiesUseCase(repository)

    @Provides
    fun provideGetQuoteUseCase(repository: StockMarketRepository): GetQuoteUseCase = GetQuoteUseCase(repository)

    @Provides
    fun provideGetDailyBarsUseCase(repository: StockMarketRepository): GetDailyBarsUseCase =
        GetDailyBarsUseCase(repository)
}
