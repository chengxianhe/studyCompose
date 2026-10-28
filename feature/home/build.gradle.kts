plugins {
    id("studycompose.android.feature")
    id("studycompose.android.lint")
}

android {
    namespace = "com.study.cc.feature.home"
}

dependencies {
    implementation(libs.androidx.activity.compose)

    testImplementation(libs.junit)
    testImplementation(libs.truth)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.turbine)
}
