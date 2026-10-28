package com.study.cc.domain.usecase

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import org.junit.Test

class ValidateStockCodeUseCaseTest {
    private val validate = ValidateStockCodeUseCase(ResolveSecurityIdUseCase())

    @Test
    fun acceptsSupportedCodesAndTrimsWhitespace() {
        assertThat(validate("600001")).isEqualTo(StockCodeValidation.Valid(SecurityId(Market.SSE, "600001")))
        assertThat(validate(" 000001 ")).isEqualTo(StockCodeValidation.Valid(SecurityId(Market.SZSE, "000001")))
    }

    @Test
    fun reportsEmptyForBlankInput() {
        listOf("", "   ").forEach { assertThat(validate(it)).isEqualTo(StockCodeValidation.Empty) }
    }

    @Test
    fun reportsInvalidFormat() {
        listOf("60001", "6000001", "60000A", "60 001").forEach {
            assertThat(validate(it)).isEqualTo(StockCodeValidation.InvalidFormat)
        }
    }

    @Test
    fun reportsUnsupportedMarketForWellFormedCodes() {
        listOf("400001", "800001", "900001").forEach {
            assertThat(validate(it)).isEqualTo(StockCodeValidation.UnsupportedMarket)
        }
    }
}
