package com.study.cc.feature.library

import com.study.cc.domain.model.PhotoDayBucket

/** Keeps one offset per day, not one object per photo, for fast date-scrubber jumps. */
internal class PhotoDayGridLayout(private val buckets: List<PhotoDayBucket>) {
    private val starts = IntArray(buckets.size + 1)

    init {
        buckets.forEachIndexed { index, bucket -> starts[index + 1] = starts[index] + 1 + bucket.total }
    }

    val itemCount: Int get() = starts.last()

    fun startIndexOf(bucketIndex: Int): Int = starts[bucketIndex]

    fun bucketIndexOf(itemIndex: Int): Int {
        var low = 0
        var high = buckets.lastIndex
        while (low < high) {
            val mid = (low + high + 1) ushr 1
            if (starts[mid] <= itemIndex) low = mid else high = mid - 1
        }
        return low
    }
}
