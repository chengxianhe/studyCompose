package com.study.cc.domain.usecase

import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId

private const val STOCK_CODE_LENGTH = 6

class ResolveSecurityIdUseCase {
    operator fun invoke(stockCode: String): SecurityId? {
        if (stockCode.length != STOCK_CODE_LENGTH || stockCode.any { it !in '0'..'9' }) return null
        val market =
            when (stockCode.first()) {
                '6' -> Market.SSE
                '0', '3' -> Market.SZSE
                else -> null
            }
        return market?.let { SecurityId(it, stockCode) }
    }
}
