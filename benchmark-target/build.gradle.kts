plugins {
    id("studycompose.android.application")
    id("studycompose.android.application.compose")
    id("studycompose.android.room")
    id("studycompose.android.lint")
}

android {
    namespace = "com.study.cc.benchmark.target"

    compileOptions {
        isCoreLibraryDesugaringEnabled = true
    }

    defaultConfig {
        applicationId = "com.study.cc.benchmark.target"
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        // Macrobenchmark 需要接近 release 的、不可调试的构建；用 debug 签名以便本机直接安装
        create("benchmark") {
            initWith(getByName("release"))
            signingConfig = signingConfigs.getByName("debug")
            matchingFallbacks += listOf("release")
        }
    }
}

dependencies {
    coreLibraryDesugaring(libs.desugar.jdk.libs)
    implementation(project(":core:designsystem"))

    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    // Macrobenchmark 冷启动要靠它响应 DROP_SHADER_CACHE 广播
    implementation(libs.androidx.profileinstaller)
    implementation(libs.kotlinx.coroutines.android)

    testImplementation(libs.junit)
    testImplementation(libs.truth)
}
