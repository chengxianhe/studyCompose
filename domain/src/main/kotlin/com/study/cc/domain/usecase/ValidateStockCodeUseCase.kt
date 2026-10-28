package com.study.cc.domain.usecase

import com.study.cc.domain.model.SecurityId

private const val STOCK_CODE_LENGTH = 6

sealed interface StockCodeValidation {
    data class Valid(val securityId: SecurityId) : StockCodeValidation

    data object Empty : StockCodeValidation

    data object InvalidFormat : StockCodeValidation

    data object UnsupportedMarket : StockCodeValidation
}

class ValidateStockCodeUseCase(private val resolveSecurityId: ResolveSecurityIdUseCase) {
    operator fun invoke(input: String): StockCodeValidation {
        val code = input.trim()
        val securityId = resolveSecurityId(code)
        // 解析失败时只负责区分原因：为空、格式不对，还是格式对但不在支持的市场
        return when {
            securityId != null -> StockCodeValidation.Valid(securityId)
            code.isEmpty() -> StockCodeValidation.Empty
            code.length == STOCK_CODE_LENGTH && code.all { it in '0'..'9' } -> StockCodeValidation.UnsupportedMarket
            else -> StockCodeValidation.InvalidFormat
        }
    }
}
