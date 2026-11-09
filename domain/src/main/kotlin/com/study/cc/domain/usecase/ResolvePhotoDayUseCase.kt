package com.study.cc.domain.usecase

import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoDayResolution
import java.time.Instant
import java.time.ZoneId

private const val MS_PER_SECOND = 1000L

/** Uses capture time, then modified time, in the device time zone. Invalid times enter the unknown bucket. */
class ResolvePhotoDayUseCase {
    operator fun invoke(takenAtMs: Long, dateModifiedSec: Long, zone: ZoneId): PhotoDayResolution {
        val effective = when {
            takenAtMs > 0 -> takenAtMs
            dateModifiedSec in 1..(Long.MAX_VALUE / MS_PER_SECOND) -> dateModifiedSec * MS_PER_SECOND
            else -> 0L
        }
        if (effective == 0L) return PhotoDayResolution(PhotoDay.Unknown, 0L)
        val date = Instant.ofEpochMilli(effective).atZone(zone).toLocalDate()
        return PhotoDayResolution(PhotoDay(date.year, date.monthValue, date.dayOfMonth), effective)
    }
}
