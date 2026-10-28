package com.study.cc.data.di

import com.study.cc.domain.usecase.ResolveSecurityIdUseCase
import com.study.cc.domain.usecase.ValidateStockCodeUseCase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
internal object StockCodeValidationModule {
    @Provides
    fun provideValidateStockCodeUseCase(resolveSecurityIdUseCase: ResolveSecurityIdUseCase): ValidateStockCodeUseCase =
        ValidateStockCodeUseCase(resolveSecurityIdUseCase)
}
