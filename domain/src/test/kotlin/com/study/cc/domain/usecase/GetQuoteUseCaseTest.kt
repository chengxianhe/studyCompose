package com.study.cc.domain.usecase

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.SecurityId
import kotlinx.coroutines.test.runTest
import org.junit.Test
import java.time.Instant

class GetQuoteUseCaseTest {
    @Test
    fun delegatesSecurityAndReturnsQuote() = runTest {
        val repository = FakeStockMarketRepository()
        val security = SecurityId(Market.SSE, "600519")
        val now = Instant.EPOCH
        val quote = Quote(security, "贵州茅台", 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 1, 1.0, 0.0, "tencent", now, now)
        repository.quoteResult = quote
        assertThat(GetQuoteUseCase(repository)(security)).isSameInstanceAs(quote)
        assertThat(repository.lastSecurity).isEqualTo(security)
    }
}
