package com.study.cc.domain.repository

import com.study.cc.domain.model.DailyBars
import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.SecuritySummary

interface StockMarketRepository {
    suspend fun searchSecurities(query: String): List<SecuritySummary>

    suspend fun getQuote(security: SecurityId): Quote

    suspend fun getDailyBars(security: SecurityId, limit: Int): DailyBars
}
