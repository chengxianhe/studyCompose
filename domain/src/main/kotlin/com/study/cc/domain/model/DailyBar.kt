package com.study.cc.domain.model

import java.time.LocalDate

data class DailyBar(
    val date: LocalDate,
    val open: Double,
    val high: Double,
    val low: Double,
    val close: Double,
    val volumeLots: Long,
    val amountYuan: Double?,
    val turnoverPercent: Double?,
)
