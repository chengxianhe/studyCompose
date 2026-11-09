package com.study.cc.feature.library

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoDayBucket
import org.junit.Test

private const val YEAR = 2026
private const val MONTH = 10
private const val DAY = 29
private const val FIRST_BUCKET_SIZE = 3
private const val ITEM_COUNT = 7
private const val UNKNOWN_HEADER_INDEX = 4

class PhotoDayGridLayoutTest {
    @Test
    fun mapsDateBucketsToHeaderAndPhotoPositionsWithoutFlatteningPhotos() {
        val layout = PhotoDayGridLayout(
            listOf(
                PhotoDayBucket(PhotoDay(YEAR, MONTH, DAY), FIRST_BUCKET_SIZE),
                PhotoDayBucket(PhotoDay.Unknown, 2),
            ),
        )

        assertThat(layout.itemCount).isEqualTo(ITEM_COUNT)
        assertThat(layout.startIndexOf(0)).isEqualTo(0)
        assertThat(layout.startIndexOf(1)).isEqualTo(UNKNOWN_HEADER_INDEX)
        assertThat((0 until ITEM_COUNT).map(layout::bucketIndexOf)).containsExactly(0, 0, 0, 0, 1, 1, 1).inOrder()
    }
}
