package com.study.cc.data.sync

const val MEDIA_TYPE_IMAGE = 1
const val MEDIA_TYPE_VIDEO = 3

/**
 * One media library row with only the fields sync needs (no paths or locations).
 * `takenAtMs <= 0` means there is no taken time.
 */
data class MediaRow(
    val mediaStoreId: Long,
    val mediaType: Int,
    val takenAtMs: Long,
    val dateModifiedSec: Long,
    val bucketId: Long,
    val generationModified: Long,
)

interface MediaRows :
    Iterator<MediaRow>,
    AutoCloseable

/** Abstraction of the system media library; the real one reads MediaStore, benchmarks use a synthetic one. */
interface MediaSource {
    fun count(): Int

    /** Media library version; a change forces a full reconcile. Empty when unsupported. */
    fun version(): String

    /** Current generation of the media library; 0 below API 30. */
    fun generation(): Long

    /** All rows ordered by `mediaStoreId` ascending (reconcile relies on this order). */
    fun openAll(): MediaRows

    /**
     * Rows that may have changed since the last sync, in any order. Filters by generation when supported, otherwise by
     * modified time.
     */
    fun openChanged(sinceGeneration: Long, sinceModifiedSec: Long): MediaRows
}
