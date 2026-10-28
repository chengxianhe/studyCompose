package com.study.cc.benchmark.target.probe

import androidx.sqlite.db.SimpleSQLiteQuery
import com.study.cc.benchmark.target.store.BenchmarkDatabase
import com.study.cc.benchmark.target.store.DayBucket
import com.study.cc.benchmark.target.store.GeneratorConfig
import com.study.cc.benchmark.target.store.PhotoMetaDao
import com.study.cc.benchmark.target.store.SyntheticPhotoGenerator

private const val UPSERT_ROWS = 1000

/** 依次跑一遍产品会用到的全部查询，每条单独计时。目标年月日取自数据本身，保证可复现。 */
class QueryProbe(private val database: BenchmarkDatabase) {
    private val dao: PhotoMetaDao = database.photoMetaDao()

    /** 返回「日桶数 / 最忙一天的张数」，只用来在界面上证明查询确实执行过。 */
    fun runAll(config: GeneratorConfig): String {
        val years = traced(TraceNames.YEAR_SUMMARIES) { dao.yearSummaries() }
        val newestYear = years.first().period
        val months = traced(TraceNames.MONTH_SUMMARIES) { dao.monthSummaries(newestYear) }
        val days = traced(TraceNames.DAY_SUMMARIES) { dao.daySummaries(newestYear, months.first().period) }
        val buckets = traced(TraceNames.DAY_BUCKETS) { dao.dayBuckets() }
        val busiest = buckets.filter { it.year > 0 }.maxBy { it.total }
        val ids = traced(TraceNames.IDS_OF_DAY) { dao.idsOfDay(busiest.year, busiest.month, busiest.day) }
        val memories = traced(TraceNames.ON_THIS_DAY) { dao.onThisDay(busiest.month, busiest.day) }
        traced(TraceNames.YEAR_VIA_STRFTIME) { dao.yearSummariesViaStrftime() }
        val rows = SyntheticPhotoGenerator(config).rows().take(UPSERT_ROWS).toList()
        traced(TraceNames.UPSERT_1000) { dao.upsertAll(rows.mapIndexed { i, row -> row.copy(id = i + 1L) }) }
        return "years=${years.size} months=${months.size} days=${days.size} buckets=${buckets.size} " +
            "busiest=${busiest.total}/${ids.size} memories=${memories.size}"
    }

    /** 反例对照：把全部 id + 时间读进两个 LongArray，看耗时与内存为什么不能全量驻留。 */
    fun loadAllIntoLongArrays(): Int {
        val total = dao.count()
        return traced(TraceNames.LOAD_ALL_LONG_ARRAYS) {
            val ids = LongArray(total)
            val times = LongArray(total)
            database.openHelper.readableDatabase
                .query(SimpleSQLiteQuery("SELECT id, takenAtUtcMs FROM photo_meta"))
                .use { cursor ->
                    var i = 0
                    while (cursor.moveToNext() && i < total) {
                        ids[i] = cursor.getLong(0)
                        times[i] = cursor.getLong(1)
                        i++
                    }
                    i
                }
        }
    }

    fun dayBuckets(): List<DayBucket> = traced(TraceNames.DAY_BUCKETS) { dao.dayBuckets() }
}
