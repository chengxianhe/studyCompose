package com.study.cc.data.stock

import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import okhttp3.HttpUrl.Companion.toHttpUrl

internal object TencentUrls {
    private const val QUOTE_BASE = "https://qt.gtimg.cn/"
    private const val DAILY_BASE = "https://web.ifzq.gtimg.cn/appstock/app/newfqkline/get"
    private const val SEARCH_BASE = "https://smartbox.gtimg.cn/s3/"

    fun quote(security: SecurityId): String =
        QUOTE_BASE.toHttpUrl().newBuilder().addPathSegment("q=${symbol(security)}").build().toString()

    fun daily(security: SecurityId, limit: Int): String = DAILY_BASE.toHttpUrl().newBuilder()
        .addEncodedQueryParameter("param", "${symbol(security)},day,,,$limit,qfq")
        .build().toString()

    fun search(query: String): String = SEARCH_BASE.toHttpUrl().newBuilder()
        .addQueryParameter("q", query).addQueryParameter("t", "all")
        .build().toString()

    fun symbol(security: SecurityId): String = (if (security.market == Market.SSE) "sh" else "sz") + security.code
}
