package com.study.cc.data.store

/** One year, month or day summary row; `coverId` is the latest item of the group. */
data class PeriodSummary(val period: Int, val total: Int, val coverId: Long, val latestTakenAt: Long)

/** One bucket of the day stream; `year == 0` is the unknown-date bucket. */
data class DayBucket(val year: Int, val month: Int, val day: Int, val total: Int)

/** Minimal fields compared during reconcile. */
data class ItemStamp(
    val mediaStoreId: Long,
    val dateModifiedSec: Long,
    val localYear: Int,
    val localMonth: Int,
    val localDay: Int,
)
