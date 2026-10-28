package com.study.cc.feature.home

import android.os.Build
import com.google.common.truth.Truth.assertThat
import org.junit.Test

class MediaPermissionsTest {
    @Test
    fun legacySdkAsksForStorageOnly() {
        assertThat(MediaPermissions.requestedFor(Build.VERSION_CODES.S).toList())
            .containsExactly("android.permission.READ_EXTERNAL_STORAGE")
    }

    @Test
    fun api33AsksForImagesAndVideo() {
        assertThat(MediaPermissions.requestedFor(Build.VERSION_CODES.TIRAMISU).toList())
            .containsExactly("android.permission.READ_MEDIA_IMAGES", "android.permission.READ_MEDIA_VIDEO")
    }

    @Test
    fun api34AlsoAsksForUserSelectedAccess() {
        assertThat(MediaPermissions.requestedFor(Build.VERSION_CODES.UPSIDE_DOWN_CAKE).toList())
            .containsExactly(
                "android.permission.READ_MEDIA_IMAGES",
                "android.permission.READ_MEDIA_VIDEO",
                "android.permission.READ_MEDIA_VISUAL_USER_SELECTED",
            )
    }
}
