package com.study.cc.domain.usecase

import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.repository.StockMarketRepository

class GetQuoteUseCase(private val repository: StockMarketRepository) {
    suspend operator fun invoke(security: SecurityId): Quote = repository.getQuote(security)
}
