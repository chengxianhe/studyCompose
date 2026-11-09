package com.study.cc.core.common

import android.os.Build

/** Runtime permissions the media library needs on each Android version. */
object MediaPermissions {
    private const val READ_MEDIA_IMAGES = "android.permission.READ_MEDIA_IMAGES"
    private const val READ_MEDIA_VIDEO = "android.permission.READ_MEDIA_VIDEO"
    private const val READ_MEDIA_VISUAL_USER_SELECTED = "android.permission.READ_MEDIA_VISUAL_USER_SELECTED"
    private const val READ_EXTERNAL_STORAGE = "android.permission.READ_EXTERNAL_STORAGE"

    fun requestedFor(sdk: Int): Array<String> = when {
        sdk >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE ->
            arrayOf(READ_MEDIA_IMAGES, READ_MEDIA_VIDEO, READ_MEDIA_VISUAL_USER_SELECTED)
        sdk >= Build.VERSION_CODES.TIRAMISU -> arrayOf(READ_MEDIA_IMAGES, READ_MEDIA_VIDEO)
        else -> arrayOf(READ_EXTERNAL_STORAGE)
    }
}
