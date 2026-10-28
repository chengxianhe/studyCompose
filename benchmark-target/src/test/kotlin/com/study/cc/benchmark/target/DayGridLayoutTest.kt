package com.study.cc.benchmark.target

import com.google.common.truth.Truth.assertThat
import com.study.cc.benchmark.target.store.DayBucket
import com.study.cc.benchmark.target.ui.DayGridLayout
import org.junit.Test

private const val YEAR = 2026
private const val TOTAL_ITEMS = 9
private const val SECOND_HEADER = 4
private const val THIRD_HEADER = 6

class DayGridLayoutTest {
    private val layout =
        DayGridLayout(
            listOf(
                DayBucket(year = YEAR, month = 10, day = 28, total = 3),
                DayBucket(year = YEAR, month = 10, day = 27, total = 1),
                DayBucket(year = 0, month = 0, day = 0, total = 2),
            ),
        )

    @Test
    fun itemCountIsHeadersPlusCells() {
        assertThat(layout.itemCount).isEqualTo(TOTAL_ITEMS)
    }

    @Test
    fun headersAreAtBucketStarts() {
        val headers = (0 until layout.itemCount).filter { layout.isHeader(it) }

        assertThat(headers).containsExactly(0, SECOND_HEADER, THIRD_HEADER).inOrder()
    }

    @Test
    fun cellsMapBackToTheirBucket() {
        val owners = (0 until layout.itemCount).map { layout.bucketIndexOf(it) }

        assertThat(owners).containsExactly(0, 0, 0, 0, 1, 1, 2, 2, 2).inOrder()
    }

    @Test
    fun singleBucketLayoutWorks() {
        val single = DayGridLayout(listOf(DayBucket(year = YEAR, month = 1, day = 1, total = 0)))

        assertThat(single.itemCount).isEqualTo(1)
        assertThat(single.isHeader(0)).isTrue()
    }
}
