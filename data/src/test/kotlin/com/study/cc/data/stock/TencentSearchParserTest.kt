package com.study.cc.data.stock

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.SecuritySummary
import com.study.cc.domain.model.StockDataException
import org.junit.Assert.assertThrows
import org.junit.Test

class TencentSearchParserTest {
    @Test
    fun oneAshareWithDecodedName() {
        assertThat(parseTencentSearch(fixture("search_600519.txt")))
            .containsExactly(SecuritySummary(SecurityId(Market.SSE, "600519"), "贵州茅台"))
    }

    @Test
    fun excludesForeignAndFundEntries() {
        assertThat(parseTencentSearch(fixture("search_pingan_multi.txt"))).containsExactly(
            SecuritySummary(SecurityId(Market.SSE, "601318"), "中国平安"),
            SecuritySummary(SecurityId(Market.SZSE, "000001"), "平安银行"),
            SecuritySummary(SecurityId(Market.SZSE, "001359"), "平安电工"),
        ).inOrder()
    }

    @Test
    fun noMatchAndGarbage() {
        assertThat(parseTencentSearch(fixture("search_no_match.txt"))).isEmpty()
        assertThrows(StockDataException.SchemaChanged::class.java) { parseTencentSearch("garbage") }
    }

    @Test
    fun `B 股被过滤`() {
        assertThat(parseTencentSearch(fixture("search_b_share_900916.txt"))).isEmpty()
    }

    @Test
    fun `科创板 A 股保留`() {
        assertThat(parseTencentSearch(fixture("search_star_688981.txt")))
            .containsExactly(SecuritySummary(SecurityId(Market.SSE, "688981"), "中芯国际"))
    }

    @Test
    fun `其他市场的残缺条目不影响深市结果`() {
        val input = """v_hint="sz~000001~平安银行~payh~GP-A^hk~02318""""
        assertThat(parseTencentSearch(input))
            .containsExactly(SecuritySummary(SecurityId(Market.SZSE, "000001"), "平安银行"))
    }
}
