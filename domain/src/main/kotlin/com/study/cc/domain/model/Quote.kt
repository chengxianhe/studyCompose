package com.study.cc.domain.model

import java.time.Instant

data class Quote(
    val security: SecurityId,
    val name: String,
    val price: Double,
    val previousClose: Double,
    val open: Double,
    val high: Double,
    val low: Double,
    val change: Double,
    val changePercent: Double,
    val volumeLots: Long,
    val amountYuan: Double,
    val turnoverPercent: Double,
    val source: String,
    val sourceTime: Instant,
    val fetchedAt: Instant,
)
