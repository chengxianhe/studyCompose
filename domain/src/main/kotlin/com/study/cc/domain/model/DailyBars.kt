package com.study.cc.domain.model

import java.time.Instant

data class DailyBars(
    val security: SecurityId,
    val adjustment: Adjustment,
    val source: String,
    val fetchedAt: Instant,
    val bars: List<DailyBar>,
)
