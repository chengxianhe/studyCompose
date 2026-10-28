package com.study.cc.benchmark.target.ui

import com.study.cc.benchmark.target.store.DayBucket

/**
 * 把「日桶列表」摊平成一条网格 item 序列：每个桶 = 1 个日期头 + N 个格子。
 * 只存每个桶的起点（几千个 Int），item → 桶用二分查找，不为 100 万个格子各建对象。
 */
class DayGridLayout(private val buckets: List<DayBucket>) {
    private val starts = IntArray(buckets.size + 1)

    init {
        for (i in buckets.indices) starts[i + 1] = starts[i] + 1 + buckets[i].total
    }

    val itemCount: Int get() = starts[buckets.size]

    fun bucketIndexOf(item: Int): Int {
        var low = 0
        var high = buckets.size - 1
        while (low < high) {
            val mid = (low + high + 1) ushr 1
            if (starts[mid] <= item) low = mid else high = mid - 1
        }
        return low
    }

    fun isHeader(item: Int): Boolean = starts[bucketIndexOf(item)] == item

    fun bucket(index: Int): DayBucket = buckets[index]
}
