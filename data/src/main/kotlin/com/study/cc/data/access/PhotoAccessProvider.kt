package com.study.cc.data.access

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import com.study.cc.domain.model.PhotoAccess
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject

private const val READ_MEDIA_IMAGES = "android.permission.READ_MEDIA_IMAGES"
private const val READ_MEDIA_VIDEO = "android.permission.READ_MEDIA_VIDEO"
private const val READ_MEDIA_VISUAL_USER_SELECTED = "android.permission.READ_MEDIA_VISUAL_USER_SELECTED"
private const val READ_EXTERNAL_STORAGE = "android.permission.READ_EXTERNAL_STORAGE"

/** Maps granted permissions to none / partial / full access per SDK level; pure so each level is unit-testable. */
internal object PhotoAccessRules {
    fun evaluate(sdk: Int, isGranted: (String) -> Boolean): PhotoAccess = when {
        sdk >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE -> fromMediaPermissions(isGranted, allowSelected = true)
        sdk >= Build.VERSION_CODES.TIRAMISU -> fromMediaPermissions(isGranted, allowSelected = false)
        isGranted(READ_EXTERNAL_STORAGE) -> PhotoAccess.FULL
        else -> PhotoAccess.NONE
    }

    private fun fromMediaPermissions(isGranted: (String) -> Boolean, allowSelected: Boolean): PhotoAccess {
        val images = isGranted(READ_MEDIA_IMAGES)
        val videos = isGranted(READ_MEDIA_VIDEO)
        return when {
            images && videos -> PhotoAccess.FULL
            images || videos || (allowSelected && isGranted(READ_MEDIA_VISUAL_USER_SELECTED)) -> PhotoAccess.PARTIAL
            else -> PhotoAccess.NONE
        }
    }
}

internal class PhotoAccessProvider @Inject constructor(@ApplicationContext private val context: Context) {
    fun current(): PhotoAccess = PhotoAccessRules.evaluate(Build.VERSION.SDK_INT) { permission ->
        ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
    }
}
