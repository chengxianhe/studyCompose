package com.study.cc.domain.usecase

import com.study.cc.domain.model.DailyBars
import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.SecuritySummary
import com.study.cc.domain.repository.StockMarketRepository

internal class FakeStockMarketRepository : StockMarketRepository {
    var searchCalls = 0
    var lastQuery: String? = null
    var lastSecurity: SecurityId? = null
    var lastLimit: Int? = null
    var searchResult = emptyList<SecuritySummary>()
    lateinit var quoteResult: Quote
    lateinit var barsResult: DailyBars

    override suspend fun searchSecurities(query: String): List<SecuritySummary> {
        searchCalls++
        lastQuery = query
        return searchResult
    }

    override suspend fun getQuote(security: SecurityId): Quote {
        lastSecurity = security
        return quoteResult
    }

    override suspend fun getDailyBars(security: SecurityId, limit: Int): DailyBars {
        lastSecurity = security
        lastLimit = limit
        return barsResult
    }
}
