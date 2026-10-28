package com.study.cc.data.access

import android.os.Build
import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.PhotoAccess
import org.junit.Test

private const val IMAGES = "android.permission.READ_MEDIA_IMAGES"
private const val VIDEO = "android.permission.READ_MEDIA_VIDEO"
private const val SELECTED = "android.permission.READ_MEDIA_VISUAL_USER_SELECTED"
private const val LEGACY = "android.permission.READ_EXTERNAL_STORAGE"

class PhotoAccessRulesTest {
    private fun access(sdk: Int, vararg granted: String) = PhotoAccessRules.evaluate(sdk) { it in granted }

    @Test
    fun legacyStorageSdkOnlyLooksAtReadExternalStorage() {
        assertThat(access(Build.VERSION_CODES.S, LEGACY)).isEqualTo(PhotoAccess.FULL)
        assertThat(access(Build.VERSION_CODES.S, IMAGES, VIDEO)).isEqualTo(PhotoAccess.NONE)
    }

    @Test
    fun api33NeedsBothMediaPermissionsForFullAccess() {
        assertThat(access(Build.VERSION_CODES.TIRAMISU, IMAGES, VIDEO)).isEqualTo(PhotoAccess.FULL)
        assertThat(access(Build.VERSION_CODES.TIRAMISU, IMAGES)).isEqualTo(PhotoAccess.PARTIAL)
        assertThat(access(Build.VERSION_CODES.TIRAMISU)).isEqualTo(PhotoAccess.NONE)
    }

    @Test
    fun api33IgnoresTheUserSelectedPermission() {
        assertThat(access(Build.VERSION_CODES.TIRAMISU, SELECTED)).isEqualTo(PhotoAccess.NONE)
    }

    @Test
    fun api34UserSelectedOnlyIsPartialAccess() {
        assertThat(access(Build.VERSION_CODES.UPSIDE_DOWN_CAKE, SELECTED)).isEqualTo(PhotoAccess.PARTIAL)
        assertThat(access(Build.VERSION_CODES.UPSIDE_DOWN_CAKE, IMAGES, VIDEO, SELECTED)).isEqualTo(PhotoAccess.FULL)
        assertThat(access(Build.VERSION_CODES.UPSIDE_DOWN_CAKE)).isEqualTo(PhotoAccess.NONE)
    }
}
