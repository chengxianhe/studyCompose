plugins {
    id("studycompose.android.library")
}

android {
    namespace = "com.study.cc.core.common"
}

dependencies {
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.android)

    testImplementation(libs.junit)
    testImplementation(libs.truth)
}
