package com.study.cc.domain.usecase

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import org.junit.Test

class ResolveSecurityIdUseCaseTest {
    private val resolve = ResolveSecurityIdUseCase()

    @Test
    fun resolvesShanghaiCode() {
        assertThat(resolve("600001")).isEqualTo(SecurityId(Market.SSE, "600001"))
    }

    @Test
    fun resolvesShenzhenCodes() {
        assertThat(resolve("000001")).isEqualTo(SecurityId(Market.SZSE, "000001"))
        assertThat(resolve("300001")).isEqualTo(SecurityId(Market.SZSE, "300001"))
    }

    @Test
    fun rejectsBeijingCodes() {
        listOf("400001", "800001", "900001").forEach { assertThat(resolve(it)).isNull() }
    }

    @Test
    fun rejectsMalformedCodes() {
        listOf("", "60001", "6000001", "60000A", " 60001").forEach { assertThat(resolve(it)).isNull() }
    }
}
