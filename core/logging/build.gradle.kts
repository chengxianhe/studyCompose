plugins {
    id("studycompose.android.library")
    id("studycompose.hilt")
    id("studycompose.android.lint")
}

android {
    namespace = "com.study.cc.core.logging"
}

dependencies {
    testImplementation(libs.junit)
}
