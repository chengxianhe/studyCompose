package com.study.cc.data.stock

import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.StockDataException
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException

private const val MIN_FIELDS = 39
private const val CODE = 2
private const val NAME = 1
private const val PRICE = 3
private const val PREVIOUS_CLOSE = 4
private const val OPEN = 5
private const val SOURCE_TIME = 30
private const val CHANGE = 31
private const val CHANGE_PERCENT = 32
private const val HIGH = 33
private const val LOW = 34
private const val TRADE = 35
private const val TRADE_VOLUME = 1
private const val TRADE_AMOUNT = 2
private const val TRADE_PARTS = 3
private const val TURNOVER_PERCENT = 38
private val timeFormat = DateTimeFormatter.ofPattern("yyyyMMddHHmmss")
private val shanghaiZone = ZoneId.of("Asia/Shanghai")

internal fun parseTencentQuote(text: String, security: SecurityId, fetchedAt: Instant): Quote {
    if ("none_match" in text) noQuoteData()
    val firstQuote = text.indexOf('"')
    val lastQuote = text.lastIndexOf('"')
    if (firstQuote < 0 || lastQuote <= firstQuote) quoteSchema("payload")
    val fields = text.substring(firstQuote + 1, lastQuote).split('~')
    if (fields.size < MIN_FIELDS) quoteSchema("field count")
    if (fields[CODE] != security.code) quoteSchema("security code")
    val trade = fields[TRADE].split('/')
    if (trade.size != TRADE_PARTS) quoteSchema("trade")
    val sourceTime =
        try {
            LocalDateTime.parse(fields[SOURCE_TIME], timeFormat).atZone(shanghaiZone).toInstant()
        } catch (e: DateTimeParseException) {
            quoteSchema("sourceTime", e)
        }
    return Quote(
        security = security,
        name = fields[NAME],
        price = fields.decimal(PRICE, "price"),
        previousClose = fields.decimal(PREVIOUS_CLOSE, "previousClose"),
        open = fields.decimal(OPEN, "open"),
        high = fields.decimal(HIGH, "high"),
        low = fields.decimal(LOW, "low"),
        change = fields.decimal(CHANGE, "change"),
        changePercent = fields.decimal(CHANGE_PERCENT, "changePercent"),
        volumeLots = trade[TRADE_VOLUME].toLongOrNull() ?: quoteSchema("volumeLots"),
        amountYuan = trade[TRADE_AMOUNT].finiteDouble("amountYuan"),
        turnoverPercent = fields.decimal(TURNOVER_PERCENT, "turnoverPercent"),
        source = "tencent",
        sourceTime = sourceTime,
        fetchedAt = fetchedAt,
    )
}

private fun List<String>.decimal(index: Int, field: String): Double = this[index].finiteDouble(field)

private fun String.finiteDouble(field: String): Double = toDoubleOrNull()?.takeIf(Double::isFinite)
    ?: throw StockDataException.SchemaChanged("quote $field")

private fun noQuoteData(): Nothing = throw StockDataException.NoData()

private fun quoteSchema(field: String, cause: Throwable? = null): Nothing {
    val error = StockDataException.SchemaChanged("quote $field", cause)
    throw error
}
