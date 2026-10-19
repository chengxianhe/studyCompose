package com.study.cc.domain.usecase

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.SecuritySummary
import kotlinx.coroutines.test.runTest
import org.junit.Test

class SearchSecuritiesUseCaseTest {
    @Test
    fun blankQueryDoesNotCallRepository() = runTest {
        val repository = FakeStockMarketRepository()
        assertThat(SearchSecuritiesUseCase(repository)(" \t ")).isEmpty()
        assertThat(repository.searchCalls).isEqualTo(0)
    }

    @Test
    fun trimsQueryAndReturnsResult() = runTest {
        val repository = FakeStockMarketRepository()
        val summary = SecuritySummary(SecurityId(Market.SSE, "600519"), "贵州茅台")
        repository.searchResult = listOf(summary)
        assertThat(SearchSecuritiesUseCase(repository)(" 600519 ")).containsExactly(summary)
        assertThat(repository.lastQuery).isEqualTo("600519")
    }
}
