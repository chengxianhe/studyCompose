package com.study.cc.feature.library

import android.content.Context
import coil.ImageLoader
import coil.decode.VideoFrameDecoder
import coil.memory.MemoryCache

private const val MAX_MEMORY_CACHE_PERCENT = 0.08

/** A single bounded cache for the timeline, shared across tab switches. */
internal object PhotoImageLoader {
    @Volatile private var instance: ImageLoader? = null

    fun get(context: Context): ImageLoader = instance ?: synchronized(this) {
        instance ?: ImageLoader.Builder(context.applicationContext)
            .memoryCache {
                MemoryCache.Builder(context.applicationContext).maxSizePercent(MAX_MEMORY_CACHE_PERCENT).build()
            }
            .components { add(VideoFrameDecoder.Factory()) }
            .build()
            .also { instance = it }
    }
}
