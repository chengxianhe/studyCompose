package com.study.cc.data.mediastore

import android.content.Context
import android.database.Cursor
import android.os.Build
import android.provider.MediaStore
import com.study.cc.data.sync.MediaRow
import com.study.cc.data.sync.MediaRows
import com.study.cc.data.sync.MediaSource
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject

private const val MEDIA_TYPES = "(${MediaStore.Files.FileColumns.MEDIA_TYPE_IMAGE}," +
    "${MediaStore.Files.FileColumns.MEDIA_TYPE_VIDEO})"
private const val TYPE_FILTER = "${MediaStore.Files.FileColumns.MEDIA_TYPE} IN $MEDIA_TYPES"
private const val GENERATION_COLUMN = "generation_modified"

/**
 * Reads images and videos from the MediaStore Files collection in one cursor ordered by `_ID`. The projection holds
 * only ids, type, times and bucket id; file paths and locations are never read.
 */
internal class MediaStoreSource @Inject constructor(@ApplicationContext private val context: Context) : MediaSource {
    private val uri = MediaStore.Files.getContentUri("external")
    private val supportsGeneration = Build.VERSION.SDK_INT >= Build.VERSION_CODES.R

    override fun count(): Int =
        context.contentResolver.query(uri, arrayOf(MediaStore.Files.FileColumns._ID), TYPE_FILTER, null, null)
            ?.use { it.count } ?: 0

    override fun version(): String =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) MediaStore.getVersion(context) else ""

    override fun generation(): Long =
        if (supportsGeneration) MediaStore.getGeneration(context, MediaStore.VOLUME_EXTERNAL_PRIMARY) else 0L

    override fun openAll(): MediaRows = open(TYPE_FILTER, emptyArray())

    override fun openChanged(sinceGeneration: Long, sinceModifiedSec: Long): MediaRows = if (supportsGeneration) {
        open("$TYPE_FILTER AND $GENERATION_COLUMN > ?", arrayOf(sinceGeneration.toString()))
    } else {
        open("$TYPE_FILTER AND ${MediaStore.MediaColumns.DATE_MODIFIED} > ?", arrayOf(sinceModifiedSec.toString()))
    }

    private fun open(selection: String, args: Array<String>): MediaRows {
        val projection =
            buildList {
                add(MediaStore.Files.FileColumns._ID)
                add(MediaStore.Files.FileColumns.MEDIA_TYPE)
                add(MediaStore.Images.ImageColumns.DATE_TAKEN)
                add(MediaStore.MediaColumns.DATE_MODIFIED)
                add(MediaStore.Images.ImageColumns.BUCKET_ID)
                if (supportsGeneration) add(GENERATION_COLUMN)
            }.toTypedArray()
        val cursor =
            context.contentResolver.query(uri, projection, selection, args, "${MediaStore.Files.FileColumns._ID} ASC")
        return CursorRows(cursor, supportsGeneration)
    }
}

private class CursorRows(private val cursor: Cursor?, private val hasGeneration: Boolean) : MediaRows {
    private var peeked = false
    private var hasRow = false

    override fun hasNext(): Boolean {
        if (!peeked) {
            hasRow = cursor?.moveToNext() == true
            peeked = true
        }
        return hasRow
    }

    override fun next(): MediaRow {
        if (!hasNext()) throw NoSuchElementException()
        peeked = false
        val c = checkNotNull(cursor)
        return MediaRow(
            mediaStoreId = c.getLong(COL_ID),
            mediaType = c.getInt(COL_TYPE),
            takenAtMs = c.getLong(COL_TAKEN),
            dateModifiedSec = c.getLong(COL_MODIFIED),
            bucketId = c.getLong(COL_BUCKET),
            generationModified = if (hasGeneration) c.getLong(COL_GENERATION) else 0L,
        )
    }

    override fun close() {
        cursor?.close()
    }

    private companion object {
        const val COL_ID = 0
        const val COL_TYPE = 1
        const val COL_TAKEN = 2
        const val COL_MODIFIED = 3
        const val COL_BUCKET = 4
        const val COL_GENERATION = 5
    }
}
