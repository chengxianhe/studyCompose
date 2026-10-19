package com.study.cc.domain.usecase

import com.study.cc.domain.model.SecuritySummary
import com.study.cc.domain.repository.StockMarketRepository

class SearchSecuritiesUseCase(private val repository: StockMarketRepository) {
    suspend operator fun invoke(query: String): List<SecuritySummary> {
        val trimmed = query.trim()
        return if (trimmed.isEmpty()) emptyList() else repository.searchSecurities(trimmed)
    }
}
