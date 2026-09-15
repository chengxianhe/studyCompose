plugins {
    id("studycompose.android.library")
    id("studycompose.hilt")
}

android {
    namespace = "com.study.cc.core.logging"
}

dependencies {
    testImplementation(libs.junit)
}
