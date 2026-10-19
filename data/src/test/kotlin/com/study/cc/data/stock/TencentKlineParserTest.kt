package com.study.cc.data.stock

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.Adjustment
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.StockDataException
import org.junit.Assert.assertThrows
import org.junit.Test
import java.time.Instant
import java.time.LocalDate

class TencentKlineParserTest {
    private val security = SecurityId(Market.SSE, "600519")
    private val now = Instant.EPOCH
    private val sample by lazy { fixture("kline_sh600519_day5.json") }

    @Test
    fun parsesVerifiedMixedTypeRowsAscending() {
        val result = parseTencentDailyBars(sample, security, now)
        assertThat(result.security).isEqualTo(security)
        assertThat(result.adjustment).isEqualTo(Adjustment.QFQ)
        assertThat(result.source).isEqualTo("tencent")
        assertThat(result.fetchedAt).isEqualTo(now)
        assertThat(result.bars).hasSize(EXPECTED_BAR_COUNT)
        assertThat(result.bars.map { it.date }).isInOrder()
        val first = result.bars.first()
        assertThat(first.date).isEqualTo(LocalDate.parse("2026-10-13"))
        assertThat(first.open).isEqualTo(FIRST_OPEN)
        assertThat(first.close).isEqualTo(FIRST_CLOSE)
        assertThat(first.high).isEqualTo(FIRST_HIGH)
        assertThat(first.low).isEqualTo(FIRST_LOW)
        assertThat(first.volumeLots).isEqualTo(FIRST_VOLUME_LOTS)
        assertThat(first.turnoverPercent).isEqualTo(FIRST_TURNOVER_PERCENT)
        assertThat(first.amountYuan).isEqualTo(FIRST_AMOUNT_YUAN)
        assertThat(result.bars.last().date).isEqualTo(LocalDate.parse("2026-10-19"))
        assertThat(result.bars.last().close).isEqualTo(LAST_CLOSE)
    }

    @Test
    fun swappedColumnsFailSanity() {
        assertThrows(StockDataException.SchemaChanged::class.java) {
            parseTencentDailyBars(sample.replace("\"1288.48\",\"1268.11\"", "\"1268.11\",\"1288.48\""), security, now)
        }
    }

    @Test
    fun optionalValuesCanBeMissing() {
        val edited = sample.replace("{},\"0.21\",\"339331.56\"", "{}")
        val bar = parseTencentDailyBars(edited, security, now).bars.first()
        assertThat(bar.turnoverPercent).isNull()
        assertThat(bar.amountYuan).isNull()
    }

    @Test
    fun `day 回退标记复权未知且重复日期去重`() {
        val firstRow = "[\"2026-10-13\",\"1287.00\",\"1274.89\",\"1288.48\",\"1268.11\",\"26573.00\",{}]"
        val input = """{"code":0,"data":{"sh600519":{"day":[$firstRow,$firstRow]}}}"""
        val result = parseTencentDailyBars(input, security, now)
        assertThat(result.bars).hasSize(1)
        assertThat(result.adjustment).isEqualTo(Adjustment.UNKNOWN)
    }

    @Test
    fun noDataAndErrors() {
        assertThrows(StockDataException.NoData::class.java) {
            parseTencentDailyBars(fixture("kline_none_match.json"), SecurityId(Market.SSE, "999999"), now)
        }
        assertThrows(StockDataException.UpstreamUnavailable::class.java) {
            parseTencentDailyBars("""{"code":1}""", security, now)
        }
        assertThrows(StockDataException.SchemaChanged::class.java) {
            parseTencentDailyBars("garbage", security, now)
        }
    }

    @Test
    fun `缺少数据对象或请求证券属于结构变化`() {
        listOf("""{"code":0}""", """{"code":0,"data":[]}""", """{"code":0,"data":{}}""").forEach { input ->
            assertThrows(StockDataException.SchemaChanged::class.java) {
                parseTencentDailyBars(input, security, now)
            }
        }
    }

    @Test
    fun `请求证券无日线键但有非空列表属于结构变化`() {
        val input = """{"code":0,"data":{"sh600519":{"other":[1]}}}"""
        assertThrows(StockDataException.SchemaChanged::class.java) {
            parseTencentDailyBars(input, security, now)
        }
    }

    @Test
    fun `第七列变成数字属于结构变化`() {
        val shifted = sample.replace("\"26573.00\",{}", "\"26573.00\",7")
        assertThrows(StockDataException.SchemaChanged::class.java) {
            parseTencentDailyBars(shifted, security, now)
        }
    }

    @Test
    fun `恰好六列的行有效`() {
        val input = """
            {"code":0,"data":{"sh600519":{"day":[
              ["2026-10-13","1287.00","1274.89","1288.48","1268.11","26573.00"]
            ]}}}
        """.trimIndent()
        assertThat(parseTencentDailyBars(input, security, now).bars).hasSize(1)
    }

    private companion object {
        const val EXPECTED_BAR_COUNT = 5
        const val FIRST_OPEN = 1287.00
        const val FIRST_CLOSE = 1274.89
        const val FIRST_HIGH = 1288.48
        const val FIRST_LOW = 1268.11
        const val FIRST_VOLUME_LOTS = 26573L
        const val FIRST_TURNOVER_PERCENT = 0.21
        const val FIRST_AMOUNT_YUAN = 3393315600.0
        const val LAST_CLOSE = 1324.97
    }
}
