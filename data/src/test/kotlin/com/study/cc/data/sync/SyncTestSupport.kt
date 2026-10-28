package com.study.cc.data.sync

import android.content.Context
import androidx.room.Room
import com.study.cc.data.store.MediaLibraryDatabase
import java.time.Clock
import java.time.Instant
import java.time.ZoneId
import java.util.TreeMap

const val YEAR = 2026
const val MONTH = 10
const val DAY_28 = 28
const val DAY_27 = 27
const val MS_PER_DAY = 86_400_000L
private const val MS_PER_SECOND = 1000L
val BASE_UTC_MS: Long = Instant.parse("2026-10-28T12:00:00Z").toEpochMilli()

/** `daysAgo` 天前的中午（UTC）；`offsetMs` 用来在同一天里区分先后。 */
fun taken(daysAgo: Int, offsetMs: Long = 0L): Long = BASE_UTC_MS - daysAgo * MS_PER_DAY + offsetMs

fun row(id: Long, takenAtMs: Long, modifiedSec: Long = takenAtMs / MS_PER_SECOND, bucket: Long = 1L) =
    MediaRow(id, MEDIA_TYPE_IMAGE, takenAtMs, modifiedSec, bucket, generationModified = 0L)

fun newDatabase(context: Context): MediaLibraryDatabase =
    Room.inMemoryDatabaseBuilder(context, MediaLibraryDatabase::class.java).allowMainThreadQueries().build()

fun fixedClock(): Clock = Clock.fixed(Instant.ofEpochMilli(BASE_UTC_MS), ZoneId.of("UTC"))

/** 按 `_ID` 有序的内存媒体库；修改行时用 [put] 自动推进 generation，模拟 MediaStore。 */
class FakeMediaSource : MediaSource {
    private val rows = TreeMap<Long, MediaRow>()
    private var generation = 0L
    var version = "v1"
    var supportsGeneration = true

    fun put(row: MediaRow) {
        generation++
        rows[row.mediaStoreId] = row.copy(generationModified = generation)
    }

    fun remove(id: Long) {
        rows.remove(id)
    }

    override fun count(): Int = rows.size

    override fun version(): String = version

    override fun generation(): Long = if (supportsGeneration) generation else 0L

    override fun openAll(): MediaRows = ListRows(rows.values.toList())

    override fun openChanged(sinceGeneration: Long, sinceModifiedSec: Long): MediaRows = ListRows(
        rows.values.filter {
            if (supportsGeneration) {
                it.generationModified > sinceGeneration
            } else {
                it.dateModifiedSec >
                    sinceModifiedSec
            }
        },
    )

    private class ListRows(private val list: List<MediaRow>) : MediaRows {
        private val iterator = list.iterator()

        override fun hasNext() = iterator.hasNext()

        override fun next() = iterator.next()

        override fun close() = Unit
    }
}
