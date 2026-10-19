package com.study.cc.data.stock

import com.study.cc.domain.model.Adjustment
import com.study.cc.domain.model.DailyBar
import com.study.cc.domain.model.DailyBars
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.StockDataException
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.intOrNull
import java.math.BigDecimal
import java.time.Instant
import java.time.LocalDate
import java.time.format.DateTimeParseException

private const val STATUS = "code"
private const val DATA = "data"
private const val QFQ_DAY = "qfqday"
private const val DAY = "day"
private const val MIN_ROW_FIELDS = 6
private const val DATE = 0
private const val OPEN = 1
private const val CLOSE = 2
private const val HIGH = 3
private const val LOW = 4
private const val VOLUME = 5
private const val TURNOVER = 7
private const val AMOUNT = 8
private const val YUAN_PER_WANYUAN = 10000

internal fun parseTencentDailyBars(text: String, security: SecurityId, fetchedAt: Instant): DailyBars {
    val (rows, adjustment) = readRows(text, security)
    val bars = rows.map { element ->
        val row = element as? JsonArray ?: klineSchema("row")
        if (row.size < MIN_ROW_FIELDS) klineSchema("row length")
        if (row.size > MIN_ROW_FIELDS && row[MIN_ROW_FIELDS] !is JsonObject) {
            klineSchema("row placeholder")
        }
        parseRow(row)
    }.distinctBy(DailyBar::date).sortedBy(DailyBar::date)
    return DailyBars(security, adjustment, "tencent", fetchedAt, bars)
}

private fun readRows(text: String, security: SecurityId): Pair<JsonArray, Adjustment> {
    val root = parseRoot(text)
    val code = (root[STATUS] as? JsonPrimitive)?.intOrNull
        ?: klineSchema("code")
    if (code != 0) throw StockDataException.UpstreamUnavailable()
    val data = root[DATA] as? JsonObject ?: klineSchema("data")
    val stock = data[TencentUrls.symbol(security)] as? JsonObject ?: klineSchema("security")
    val (rows, adjustment) = if (stock.containsKey(QFQ_DAY)) {
        stock[QFQ_DAY] to Adjustment.QFQ
    } else {
        stock[DAY] to Adjustment.UNKNOWN
    }
    val array = rows as? JsonArray ?: klineSchema("day list")
    if (array.isEmpty()) throw StockDataException.NoData()
    return array to adjustment
}

private fun parseRoot(text: String): JsonObject {
    val root = try {
        Json.parseToJsonElement(text) as? JsonObject
    } catch (e: SerializationException) {
        klineSchema("JSON", e)
    } catch (e: IllegalArgumentException) {
        klineSchema("JSON", e)
    } ?: klineSchema("root")
    return root
}

private fun parseRow(row: JsonArray): DailyBar {
    val date = try {
        LocalDate.parse(row.string(DATE, "date"))
    } catch (e: DateTimeParseException) {
        klineSchema("date", e)
    }
    val open = row.number(OPEN, "open")
    val close = row.number(CLOSE, "close")
    val high = row.number(HIGH, "high")
    val low = row.number(LOW, "low")
    if (high < low || open !in low..high || close !in low..high) {
        klineSchema("OHLC")
    }
    val volume = row.volumeLots()
    val amount = row.amountYuan()
    return DailyBar(
        date,
        open,
        high,
        low,
        close,
        volume,
        amount,
        row.optionalNumber(TURNOVER, "turnoverPercent"),
    )
}

private fun JsonArray.volumeLots(): Long = try {
    BigDecimal(string(VOLUME, "volumeLots")).longValueExact()
} catch (e: NumberFormatException) {
    klineSchema("volumeLots", e)
} catch (e: ArithmeticException) {
    klineSchema("volumeLots", e)
}

private fun JsonArray.amountYuan(): Double? = optionalText(AMOUNT, "amountYuan")?.let {
    val wanYuan = try {
        BigDecimal(it)
    } catch (e: NumberFormatException) {
        klineSchema("amountYuan", e)
    }
    wanYuan.multiply(BigDecimal.valueOf(YUAN_PER_WANYUAN.toLong())).toDouble()
}

private fun JsonArray.string(index: Int, field: String): String {
    val value = (getOrNull(index) as? JsonPrimitive)?.content
    return value ?: klineSchema(field)
}

private fun JsonArray.number(index: Int, field: String): Double {
    val value = string(index, field).toDoubleOrNull()?.takeIf(Double::isFinite)
    return value ?: klineSchema(field)
}

private fun JsonArray.optionalNumber(index: Int, field: String): Double? {
    val content = optionalText(index, field)
    return if (content == null) {
        null
    } else {
        content.toDoubleOrNull()?.takeIf(Double::isFinite) ?: klineSchema(field)
    }
}

private fun JsonArray.optionalText(index: Int, field: String): String? {
    val value = getOrNull(index) ?: return null
    val content = (value as? JsonPrimitive)?.content ?: klineSchema(field)
    return content.takeUnless { it.isBlank() || it == "null" }
}

private fun klineSchema(field: String, cause: Throwable? = null): Nothing {
    val error = StockDataException.SchemaChanged("kline $field", cause)
    throw error
}
