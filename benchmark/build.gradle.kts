plugins {
    id("studycompose.android.test")
}

android {
    namespace = "com.study.cc.benchmark"
    targetProjectPath = ":benchmark-target"

    defaultConfig {
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        // 部分厂商 ROM（如 EMUI）不响应 DROP_SHADER_CACHE 广播；不中断，但冷启动数字可能略偏乐观，需在基线文档注明
        testInstrumentationRunnerArguments["androidx.benchmark.dropShaders.throwOnFailure"] = "false"
    }

    buildTypes {
        // 与被测模块的 benchmark 构建类型配对；自检（instrumentation）与被测应用分属两个 APK
        create("benchmark") {
            isDebuggable = true
            signingConfig = signingConfigs.getByName("debug")
            matchingFallbacks += listOf("release")
        }
    }

    experimentalProperties["android.experimental.self-instrumenting"] = true
}

dependencies {
    implementation(libs.androidx.junit)
    implementation(libs.androidx.benchmark.macro.junit4)
    implementation(libs.androidx.test.uiautomator)
}

// 只需要 benchmark 这一个变体；其余变体不参与构建
androidComponents {
    beforeVariants(selector().all()) { variant ->
        variant.enable = variant.buildType == "benchmark"
    }
}
