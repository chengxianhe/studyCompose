plugins {
    id("studycompose.android.feature")
    id("studycompose.android.lint")
}

android {
    namespace = "com.study.cc.feature.library"
}

dependencies {
    implementation(libs.androidx.activity.compose)
    // Grid sticky headers require the Foundation version already resolved by the app's Navigation 3.
    implementation(libs.androidx.compose.foundation)
    implementation(libs.coil.compose)
    implementation(libs.coil.video)

    testImplementation(libs.junit)
    testImplementation(libs.truth)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.turbine)
}
