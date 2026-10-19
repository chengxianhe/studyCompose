package com.study.cc.domain.usecase

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.Adjustment
import com.study.cc.domain.model.DailyBars
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import kotlinx.coroutines.test.runTest
import org.junit.Test
import java.time.Instant

class GetDailyBarsUseCaseTest {
    private val security = SecurityId(Market.SSE, "600519")

    @Test
    fun defaultLimit() = runTest {
        val repository = repository()
        assertThat(GetDailyBarsUseCase(repository)(security)).isSameInstanceAs(repository.barsResult)
        assertThat(repository.lastSecurity).isEqualTo(security)
        assertThat(repository.lastLimit).isEqualTo(GetDailyBarsUseCase.DEFAULT_LIMIT)
    }

    @Test
    fun clampsBothEnds() = runTest {
        val repository = repository()
        val useCase = GetDailyBarsUseCase(repository)
        useCase(security, BELOW_MINIMUM)
        assertThat(repository.lastLimit).isEqualTo(1)
        useCase(security, ABOVE_MAXIMUM)
        assertThat(repository.lastLimit).isEqualTo(GetDailyBarsUseCase.MAX_LIMIT)
    }

    private fun repository() = FakeStockMarketRepository().apply {
        barsResult = DailyBars(security, Adjustment.QFQ, "tencent", Instant.EPOCH, emptyList())
    }

    private companion object {
        const val BELOW_MINIMUM = -5
        const val ABOVE_MAXIMUM = 999
    }
}
