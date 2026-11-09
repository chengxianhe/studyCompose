package com.study.cc.domain.model

/** The device-local day of a photo; zeroes represent a photo without a usable date. */
data class PhotoDay(val year: Int, val month: Int, val day: Int) {
    val isUnknown: Boolean get() = year == 0

    companion object {
        val Unknown = PhotoDay(0, 0, 0)
    }
}

data class PhotoDayResolution(val day: PhotoDay, val effectiveTakenAtMs: Long)

data class PhotoDayBucket(val day: PhotoDay, val total: Int)
