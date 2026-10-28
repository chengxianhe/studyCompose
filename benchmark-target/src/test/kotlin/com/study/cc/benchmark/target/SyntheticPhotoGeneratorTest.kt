package com.study.cc.benchmark.target

import com.google.common.truth.Truth.assertThat
import com.study.cc.benchmark.target.store.GeneratorConfig
import com.study.cc.benchmark.target.store.SyntheticPhotoGenerator
import org.junit.Test
import java.time.ZoneId

private const val SAMPLE = 50_000
private const val HEAD = 1000
private const val DATE_SAMPLE = 2000
private const val SEED = 7L
private const val UNKNOWN_SHARE = 0.02
private const val UNKNOWN_TOLERANCE = 0.005
private const val MIN_YEARS = 15
private const val HOT_DAY_FACTOR = 5
private const val BUCKET_SKEW_FACTOR = 5

class SyntheticPhotoGeneratorTest {
    private val config = GeneratorConfig(total = SAMPLE, seed = SEED, zone = ZoneId.of("UTC"))

    @Test
    fun sameSeedProducesSameRows() {
        val first = SyntheticPhotoGenerator(config).rows().take(HEAD).toList()
        val second = SyntheticPhotoGenerator(config).rows().take(HEAD).toList()

        assertThat(first).isEqualTo(second)
    }

    @Test
    fun producesRequestedCount() {
        assertThat(SyntheticPhotoGenerator(config).rows().count()).isEqualTo(SAMPLE)
    }

    @Test
    fun unknownDateShareIsAboutTwoPercent() {
        val rows = SyntheticPhotoGenerator(config).rows().toList()
        val share = rows.count { it.localYear == 0 }.toDouble() / rows.size

        assertThat(share).isWithin(UNKNOWN_TOLERANCE).of(UNKNOWN_SHARE)
        assertThat(rows.filter { it.localYear == 0 }.all { it.takenAtUtcMs == 0L }).isTrue()
    }

    @Test
    fun knownDatesAreConsistentWithTimestamps() {
        val known = SyntheticPhotoGenerator(config).rows().filter { it.localYear > 0 }.take(DATE_SAMPLE).toList()

        known.forEach { row ->
            val date = java.time.Instant.ofEpochMilli(row.takenAtUtcMs).atZone(ZoneId.of("UTC")).toLocalDate()
            assertThat(listOf(date.year, date.monthValue, date.dayOfMonth))
                .containsExactly(row.localYear, row.localMonth, row.localDay)
                .inOrder()
        }
    }

    @Test
    fun spansAboutFifteenYearsAndSkewsTowardHotDays() {
        val known = SyntheticPhotoGenerator(config).rows().filter { it.localYear > 0 }.toList()
        val years = known.map { it.localYear }.distinct()
        val perDay = known.groupingBy { Triple(it.localYear, it.localMonth, it.localDay) }.eachCount()

        assertThat(years.size).isAtLeast(MIN_YEARS)
        assertThat(perDay.values.max()).isGreaterThan(known.size / perDay.size * HOT_DAY_FACTOR)
    }

    @Test
    fun bucketsAreSkewed() {
        val counts = SyntheticPhotoGenerator(config).rows().groupingBy { it.bucketId }.eachCount()

        assertThat(counts.keys.min()).isEqualTo(1L)
        assertThat(counts.getValue(1L)).isGreaterThan(counts.getValue(counts.keys.max()) * BUCKET_SKEW_FACTOR)
    }
}
