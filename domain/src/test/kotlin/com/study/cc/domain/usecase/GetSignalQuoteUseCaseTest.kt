package com.study.cc.domain.usecase

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.ResearchSignal
import com.study.cc.domain.model.SecurityId
import kotlinx.coroutines.test.runTest
import org.junit.Test
import java.time.Instant

class GetSignalQuoteUseCaseTest {
    private val repository = FakeStockMarketRepository()
    private val useCase = GetSignalQuoteUseCase(ResolveSecurityIdUseCase(), GetQuoteUseCase(repository))

    @Test
    fun resolvableCodeFetchesQuoteForResolvedSecurity() = runTest {
        val security = SecurityId(Market.SSE, "600519")
        repository.quoteResult = quote(security)

        assertThat(useCase(signal("600519"))).isEqualTo(repository.quoteResult)
        assertThat(repository.lastSecurity).isEqualTo(security)
    }

    @Test
    fun unresolvableCodeReturnsNullWithoutRequest() = runTest {
        assertThat(useCase(signal("830799"))).isNull()
        assertThat(repository.lastSecurity).isNull()
    }

    private fun signal(code: String) = ResearchSignal("id", code, "n", "e", 1, 1, 1.0, 1.0, 1, 1.0)

    private fun quote(security: SecurityId) =
        Quote(security, "n", 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 1, 1.0, 0.0, "t", Instant.EPOCH, Instant.EPOCH)
}
