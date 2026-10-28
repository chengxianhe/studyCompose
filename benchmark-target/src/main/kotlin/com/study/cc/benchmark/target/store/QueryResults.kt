package com.study.cc.benchmark.target.store

/** 年 / 月 / 日汇总的一行：`coverId` 是组内拍摄时间最晚的一张。 */
data class PeriodSummary(val period: Int, val total: Int, val coverId: Long, val latestTakenAt: Long)

/** 日流的一个桶；`year == 0` 是「未知日期」桶。 */
data class DayBucket(val year: Int, val month: Int, val day: Int, val total: Int)
