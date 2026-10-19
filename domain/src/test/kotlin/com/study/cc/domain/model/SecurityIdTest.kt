package com.study.cc.domain.model

import com.google.common.truth.Truth.assertThat
import org.junit.Assert.assertThrows
import org.junit.Test

class SecurityIdTest {
    @Test
    fun `六位 ASCII 数字代码有效`() {
        assertThat(SecurityId(Market.SSE, "600519").code).isEqualTo("600519")
    }

    @Test
    fun `过短 字母和逗号代码均被拒绝`() {
        listOf("60051", "60A519", "600,519").forEach { code ->
            assertThrows(IllegalArgumentException::class.java) { SecurityId(Market.SSE, code) }
        }
    }
}
