package com.study.cc.feature.home

import com.study.cc.domain.model.DailyBars
import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.SecuritySummary
import com.study.cc.domain.repository.StockMarketRepository

internal class FakeQuoteRepository(private val onQuote: suspend (SecurityId) -> Quote) : StockMarketRepository {
    override suspend fun searchSecurities(query: String): List<SecuritySummary> = error("Unused")

    override suspend fun getQuote(security: SecurityId): Quote = onQuote(security)

    override suspend fun getDailyBars(security: SecurityId, limit: Int): DailyBars = error("Unused")
}
