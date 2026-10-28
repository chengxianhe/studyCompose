package com.study.cc.benchmark.target.ui

import androidx.compose.runtime.mutableStateMapOf
import com.study.cc.benchmark.target.probe.TraceNames
import com.study.cc.benchmark.target.probe.traced
import com.study.cc.benchmark.target.store.DayBucket
import com.study.cc.benchmark.target.store.PhotoMetaDao
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private const val MAX_CACHED_DAYS = 12

/** 按需加载某一天的 id 并只缓存最近几天，模拟「进入某天只查该天」的数据路径。 */
class DayIdsCache(private val dao: PhotoMetaDao, private val layout: DayGridLayout) {
    private val loaded = mutableStateMapOf<Int, LongArray>()
    private val order = ArrayDeque<Int>()

    fun idsFor(bucketIndex: Int): LongArray? = loaded[bucketIndex]

    suspend fun ensureLoaded(bucketIndex: Int) {
        if (loaded.containsKey(bucketIndex)) return
        val bucket = layout.bucket(bucketIndex)
        val ids = withContext(Dispatchers.IO) { traced(TraceNames.IDS_OF_DAY) { query(bucket) } }
        loaded[bucketIndex] = ids
        order.addLast(bucketIndex)
        while (order.size > MAX_CACHED_DAYS) loaded.remove(order.removeFirst())
    }

    private fun query(bucket: DayBucket): LongArray = dao.idsOfDay(bucket.year, bucket.month, bucket.day).toLongArray()
}
