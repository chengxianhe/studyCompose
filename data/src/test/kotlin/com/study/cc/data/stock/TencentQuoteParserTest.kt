package com.study.cc.data.stock

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.StockDataException
import org.junit.Assert.assertThrows
import org.junit.Test
import java.nio.charset.Charset
import java.time.Instant
import java.time.OffsetDateTime

class TencentQuoteParserTest {
    private val security = SecurityId(Market.SSE, "600519")
    private val now = Instant.EPOCH
    private val sample by lazy { fixture("quote_sh600519.gbk", Charset.forName("GBK")) }

    @Test
    fun parsesVerifiedGbkFields() {
        val quote = parseTencentQuote(sample, security, now)
        assertThat(quote.security).isEqualTo(security)
        assertThat(quote.name).isEqualTo("贵州茅台")
        assertThat(quote.price).isEqualTo(PRICE)
        assertThat(quote.previousClose).isEqualTo(PREVIOUS_CLOSE)
        assertThat(quote.open).isEqualTo(OPEN)
        assertThat(quote.high).isEqualTo(HIGH)
        assertThat(quote.low).isEqualTo(LOW)
        assertThat(quote.change).isEqualTo(CHANGE)
        assertThat(quote.changePercent).isEqualTo(CHANGE_PERCENT)
        assertThat(quote.volumeLots).isEqualTo(VOLUME_LOTS)
        assertThat(quote.amountYuan).isEqualTo(AMOUNT_YUAN)
        assertThat(quote.turnoverPercent).isEqualTo(TURNOVER_PERCENT)
        assertThat(quote.sourceTime).isEqualTo(OffsetDateTime.parse("2026-10-19T16:14:57+08:00").toInstant())
        assertThat(quote.fetchedAt).isEqualTo(now)
        assertThat(quote.source).isEqualTo("tencent")
    }

    @Test
    fun noMatch() {
        assertThrows(StockDataException.NoData::class.java) {
            parseTencentQuote(fixture("quote_none_match.txt"), security, now)
        }
    }

    @Test
    fun `没有引号且不是无结果标记属于结构变化`() {
        assertThrows(StockDataException.SchemaChanged::class.java) {
            parseTencentQuote("response without quotes", security, now)
        }
    }

    @Test
    fun `首尾空白和回车换行不影响解析`() {
        val quote = parseTencentQuote("  $sample\r\n  ", security, now)
        assertThat(quote.price).isEqualTo(PRICE)
    }

    @Test
    fun `末尾额外字段不影响解析`() {
        val expanded = sample.replace("\";", "~extra~fields\";")
        val quote = parseTencentQuote(expanded, security, now)
        assertThat(quote.price).isEqualTo(PRICE)
    }

    @Test
    fun truncatedFields() {
        assertThrows(StockDataException.SchemaChanged::class.java) {
            parseTencentQuote("v_sh600519=\"1~贵州茅台~600519\";", security, now)
        }
    }

    @Test
    fun nonNumericPriceNamesField() {
        val error = assertThrows(StockDataException.SchemaChanged::class.java) {
            parseTencentQuote(sample.replace("~1324.97~1329.00~", "~bad~1329.00~"), security, now)
        }
        assertThat(error).hasMessageThat().contains("price")
    }

    @Test
    fun codeMismatch() {
        assertThrows(StockDataException.SchemaChanged::class.java) {
            parseTencentQuote(sample.replace("~600519~", "~000001~"), security, now)
        }
    }

    private companion object {
        const val PRICE = 1324.97
        const val PREVIOUS_CLOSE = 1329.00
        const val OPEN = 1322.50
        const val HIGH = 1348.60
        const val LOW = 1321.00
        const val CHANGE = -4.03
        const val CHANGE_PERCENT = -0.30
        const val VOLUME_LOTS = 39729L
        const val AMOUNT_YUAN = 5308935919.0
        const val TURNOVER_PERCENT = 0.32
    }
}
