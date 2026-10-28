plugins {
    id("studycompose.android.library")
    id("studycompose.hilt")
    id("studycompose.android.room")
    id("studycompose.android.lint")
    alias(libs.plugins.kotlin.serialization)
}

android {
    namespace = "com.study.cc.data"

    compileOptions {
        isCoreLibraryDesugaringEnabled = true
    }

    testOptions {
        unitTests {
            // Robolectric 需要它来提供内存 Room 与权限相关的 Android 环境
            isIncludeAndroidResources = true
        }
    }
}

dependencies {
    coreLibraryDesugaring(libs.desugar.jdk.libs)
    implementation(project(":domain"))
    implementation(project(":core:common"))
    implementation(project(":core:logging"))

    implementation(libs.retrofit.core)
    implementation(libs.retrofit.converter.kotlinx.serialization)
    implementation(libs.okhttp.core)
    implementation(libs.okhttp.logging.interceptor)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.androidx.core.ktx)

    testImplementation(libs.junit)
    testImplementation(libs.truth)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.robolectric)
}
