package com.study.cc.benchmark.target.probe

import android.os.Trace

/** 每个被度量的操作包一层 trace 段，Macrobenchmark 的 TraceSectionMetric 按名字取耗时。 */
internal inline fun <T> traced(name: String, block: () -> T): T {
    Trace.beginSection(name)
    try {
        return block()
    } finally {
        Trace.endSection()
    }
}

object TraceNames {
    const val SEED = "bench.seed"
    const val YEAR_SUMMARIES = "q.yearSummaries"
    const val MONTH_SUMMARIES = "q.monthSummaries"
    const val DAY_SUMMARIES = "q.daySummaries"
    const val IDS_OF_DAY = "q.idsOfDay"
    const val ON_THIS_DAY = "q.onThisDay"
    const val DAY_BUCKETS = "q.dayBuckets"
    const val UPSERT_1000 = "q.upsert1000"
    const val YEAR_VIA_STRFTIME = "q.yearSummariesViaStrftime"
    const val LOAD_ALL_LONG_ARRAYS = "q.loadAllIntoLongArrays"
}
