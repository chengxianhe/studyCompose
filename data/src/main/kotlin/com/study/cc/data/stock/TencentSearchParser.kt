package com.study.cc.data.stock

import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.SecuritySummary
import com.study.cc.domain.model.StockDataException

private const val ENTRY_FIELDS = 5
private const val PREFIX = 0
private const val CODE = 1
private const val NAME = 2
private const val TYPE = 4
private const val HEX_RADIX = 16
private val unicodeEscape = Regex("\\\\u([0-9a-fA-F]{4})")
private val sixDigits = Regex("[0-9]{6}")

internal fun parseTencentSearch(text: String): List<SecuritySummary> {
    val match = Regex("v_hint=\"([^\"]*)\"").find(text)
        ?: searchSchema("payload")
    if (match.groupValues[1] == "N") return emptyList()
    return match.groupValues[1].split('^').mapNotNull { entry ->
        val fields = entry.split('~')
        val market = when (fields[PREFIX]) {
            "sh" -> Market.SSE
            "sz" -> Market.SZSE
            else -> return@mapNotNull null
        }
        if (fields.size < ENTRY_FIELDS) searchSchema("entry")
        if (!fields[TYPE].startsWith("GP-A")) return@mapNotNull null
        if (!sixDigits.matches(fields[CODE]) || fields[NAME].isBlank()) {
            searchSchema("security")
        }
        val name = unicodeEscape.replace(fields[NAME]) { matchResult ->
            matchResult.groupValues[1].toInt(HEX_RADIX).toChar().toString()
        }
        SecuritySummary(SecurityId(market, fields[CODE]), name)
    }
}

private fun searchSchema(field: String): Nothing = throw StockDataException.SchemaChanged("search $field")
