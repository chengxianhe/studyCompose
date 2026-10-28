package com.study.cc.benchmark.target.store

import java.time.LocalDate
import java.time.ZoneId
import kotlin.random.Random

const val DEFAULT_SEED = 20_261_028L

private const val END_YEAR = 2026
private const val END_MONTH = 10
private const val END_DAY = 28

private const val SPAN_YEARS = 15
private const val DAYS_PER_YEAR = 365
private const val LEAP_DAYS = 4
private const val SPAN_DAYS = SPAN_YEARS * DAYS_PER_YEAR + LEAP_DAYS
private const val MS_PER_DAY = 86_400_000
private const val UNKNOWN_RATIO = 0.02
private const val HOT_DAY_FRACTION = 0.03
private const val HOT_DAY_RATIO = 0.5
private const val BUCKET_COUNT = 30
private const val HEIC_THRESHOLD = 0.97
private const val PNG_THRESHOLD = 0.90
const val MEDIA_JPEG = 0
const val MEDIA_HEIC = 1
const val MEDIA_PNG = 2

class GeneratorConfig(
    val total: Int,
    val seed: Long = DEFAULT_SEED,
    val zone: ZoneId = ZoneId.systemDefault(),
    val endDate: LocalDate = LocalDate.of(END_YEAR, END_MONTH, END_DAY),
)

/**
 * 可复现的合成元数据：约 15 年跨度；一半照片落在 3% 的「热点日」（连拍 / 旅行）；约 2% 无拍摄时间；
 * 30 个相册按 Zipf 偏斜。日期按设备时区取本地年月日；每天按 24 小时计，忽略夏令时造成的偏差。
 */
class SyntheticPhotoGenerator(private val config: GeneratorConfig) {
    private val dayStartUtcMs = LongArray(SPAN_DAYS)
    private val years = IntArray(SPAN_DAYS)
    private val months = IntArray(SPAN_DAYS)
    private val days = IntArray(SPAN_DAYS)
    private val bucketCumulative = DoubleArray(BUCKET_COUNT)

    init {
        val first = config.endDate.minusDays((SPAN_DAYS - 1).toLong())
        for (i in 0 until SPAN_DAYS) {
            val date = first.plusDays(i.toLong())
            dayStartUtcMs[i] = date.atStartOfDay(config.zone).toInstant().toEpochMilli()
            years[i] = date.year
            months[i] = date.monthValue
            days[i] = date.dayOfMonth
        }
        var sum = 0.0
        for (b in 0 until BUCKET_COUNT) {
            sum += 1.0 / (b + 1)
            bucketCumulative[b] = sum
        }
    }

    fun rows(): Sequence<PhotoMetaEntity> {
        val random = Random(config.seed)
        val hotDays = IntArray((SPAN_DAYS * HOT_DAY_FRACTION).toInt()) { random.nextInt(SPAN_DAYS) }
        return generateSequence(0) { it + 1 }.take(config.total).map { nextRow(random, hotDays) }
    }

    private fun nextRow(random: Random, hotDays: IntArray): PhotoMetaEntity {
        val mediaType = pickMediaType(random.nextDouble())
        val bucketId = pickBucket(random.nextDouble())
        if (random.nextDouble() < UNKNOWN_RATIO) {
            return PhotoMetaEntity(
                takenAtUtcMs = 0,
                localYear = 0,
                localMonth = 0,
                localDay = 0,
                mediaType = mediaType,
                bucketId = bucketId,
            )
        }
        val dayIndex =
            if (random.nextDouble() <
                HOT_DAY_RATIO
            ) {
                hotDays[random.nextInt(hotDays.size)]
            } else {
                random.nextInt(SPAN_DAYS)
            }
        return PhotoMetaEntity(
            takenAtUtcMs = dayStartUtcMs[dayIndex] + random.nextInt(MS_PER_DAY),
            localYear = years[dayIndex],
            localMonth = months[dayIndex],
            localDay = days[dayIndex],
            mediaType = mediaType,
            bucketId = bucketId,
        )
    }

    private fun pickMediaType(r: Double): Int = when {
        r > HEIC_THRESHOLD -> MEDIA_PNG
        r > PNG_THRESHOLD -> MEDIA_HEIC
        else -> MEDIA_JPEG
    }

    private fun pickBucket(r: Double): Long {
        val target = r * bucketCumulative[BUCKET_COUNT - 1]
        var index = bucketCumulative.binarySearch(target)
        if (index < 0) index = -index - 1
        return (index + 1).toLong()
    }
}
