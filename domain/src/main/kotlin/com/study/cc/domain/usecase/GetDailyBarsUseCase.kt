package com.study.cc.domain.usecase

import com.study.cc.domain.model.DailyBars
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.repository.StockMarketRepository

class GetDailyBarsUseCase(private val repository: StockMarketRepository) {
    suspend operator fun invoke(security: SecurityId, limit: Int = DEFAULT_LIMIT): DailyBars =
        repository.getDailyBars(security, limit.coerceIn(MIN_LIMIT, MAX_LIMIT))

    companion object {
        const val DEFAULT_LIMIT = 250
        const val MAX_LIMIT = 800
        private const val MIN_LIMIT = 1
    }
}
