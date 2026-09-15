plugins {
    id("studycompose.android.library")
    id("studycompose.android.library.compose")
}

android {
    namespace = "com.study.cc.core.ui"
}

dependencies {
    implementation(project(":core:designsystem"))
}
