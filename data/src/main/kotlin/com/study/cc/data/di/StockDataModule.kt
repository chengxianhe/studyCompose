package com.study.cc.data.di

import com.study.cc.data.repository.StockMarketRepositoryImpl
import com.study.cc.data.stock.TencentApi
import com.study.cc.domain.repository.StockMarketRepository
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import java.time.Clock
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
internal abstract class StockDataModule {
    @Binds
    abstract fun bindStockMarketRepository(impl: StockMarketRepositoryImpl): StockMarketRepository

    companion object {
        private const val CONNECT_TIMEOUT_SECONDS = 5L
        private const val CALL_TIMEOUT_SECONDS = 10L

        @Provides
        fun provideClock(): Clock = Clock.systemUTC()

        @Provides
        @Singleton
        fun provideTencentApi(): TencentApi {
            val client = OkHttpClient.Builder()
                .connectTimeout(CONNECT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
                .callTimeout(CALL_TIMEOUT_SECONDS, TimeUnit.SECONDS)
                .retryOnConnectionFailure(false)
                .build()
            return Retrofit.Builder()
                .baseUrl("https://web.ifzq.gtimg.cn/")
                .client(client)
                .build().create(TencentApi::class.java)
        }
    }
}
