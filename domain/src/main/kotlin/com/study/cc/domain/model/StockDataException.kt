package com.study.cc.domain.model

sealed class StockDataException(message: String, cause: Throwable? = null) : Exception(message, cause) {
    class NoData(message: String = "No stock data") : StockDataException(message)

    class SchemaChanged(message: String, cause: Throwable? = null) : StockDataException(message, cause)

    class UpstreamUnavailable(message: String = "Stock source unavailable", cause: Throwable? = null) :
        StockDataException(message, cause)
}
