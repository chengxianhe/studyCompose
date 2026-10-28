package com.study.cc.feature.stocklookup

import com.study.cc.domain.model.SecurityId

enum class StockLookupError { Empty, InvalidFormat, UnsupportedMarket }

data class StockLookupUiState(
    val input: String = "",
    val error: StockLookupError? = null,
    val resolved: SecurityId? = null,
)
