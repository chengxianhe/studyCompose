package com.study.cc.domain.usecase

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.PhotoDay
import org.junit.Test
import java.time.Instant
import java.time.ZoneId

private const val YEAR = 2026
private const val MONTH = 10
private const val CAPTURE_DAY = 28
private const val MODIFIED_DAY = 29
private const val MS_PER_SECOND = 1000L

class ResolvePhotoDayUseCaseTest {
    private val resolve = ResolvePhotoDayUseCase()

    @Test
    fun sameInstantUsesDeviceTimeZone() {
        val timestamp = Instant.parse("2026-10-28T23:30:00Z").toEpochMilli()

        assertThat(resolve(timestamp, 0, ZoneId.of("UTC")).day).isEqualTo(PhotoDay(YEAR, MONTH, CAPTURE_DAY))
        assertThat(resolve(timestamp, 0, ZoneId.of("Asia/Shanghai")).day).isEqualTo(PhotoDay(YEAR, MONTH, MODIFIED_DAY))
    }

    @Test
    fun captureTimeTakesPrecedenceAcrossMidnight() {
        val capture = Instant.parse("2026-10-28T23:59:59Z").toEpochMilli()
        val modified = Instant.parse("2026-10-29T00:00:01Z").epochSecond

        val result = resolve(capture, modified, ZoneId.of("UTC"))

        assertThat(result.day).isEqualTo(PhotoDay(YEAR, MONTH, CAPTURE_DAY))
        assertThat(result.effectiveTakenAtMs).isEqualTo(capture)
    }

    @Test
    fun missingCaptureTimeFallsBackToModifiedTime() {
        val modified = Instant.parse("2026-10-29T00:00:01Z").epochSecond

        val result = resolve(0, modified, ZoneId.of("UTC"))

        assertThat(result.day).isEqualTo(PhotoDay(YEAR, MONTH, MODIFIED_DAY))
        assertThat(result.effectiveTakenAtMs).isEqualTo(modified * MS_PER_SECOND)
    }

    @Test
    fun missingOrInvalidTimesEnterUnknownBucket() {
        assertThat(resolve(0, 0, ZoneId.of("UTC")).day).isEqualTo(PhotoDay.Unknown)
        assertThat(resolve(-1, -1, ZoneId.of("UTC")).day).isEqualTo(PhotoDay.Unknown)
        assertThat(resolve(0, Long.MAX_VALUE, ZoneId.of("UTC")).day).isEqualTo(PhotoDay.Unknown)
    }
}
