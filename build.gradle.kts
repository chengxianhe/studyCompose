import com.diffplug.gradle.spotless.SpotlessExtension
import io.gitlab.arturbosch.detekt.Detekt
import io.gitlab.arturbosch.detekt.extensions.DetektExtension

// Top-level build file where you can add configuration options common to all sub-projects/modules.
// Plugins are declared here with apply false so their versions resolve once for the whole build;
// build-logic convention plugins apply them per-module by plugin id without repeating versions.
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.library) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.jvm) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.ksp) apply false
    alias(libs.plugins.hilt.android) apply false
    alias(libs.plugins.androidx.room) apply false
    alias(libs.plugins.detekt) apply false
    alias(libs.plugins.spotless) apply false
}

subprojects {
    apply(plugin = "io.gitlab.arturbosch.detekt")
    apply(plugin = "com.diffplug.spotless")
    apply(plugin = "jacoco")

    extensions.configure<DetektExtension> {
        buildUponDefaultConfig = true
        autoCorrect = false
        config.setFrom(files("$rootDir/config/detekt/detekt.yml"))
    }

    // :app 里 Android Studio 默认模板生成的 Counter 教学 demo，按约定暂不修改，先豁免检查。
    tasks.withType<Detekt>().configureEach {
        exclude("**/ui/theme/**", "**/MainActivity.kt", "**/ExampleUnitTest.kt", "**/ExampleInstrumentedTest.kt")
    }

    extensions.configure<SpotlessExtension> {
        kotlin {
            target("src/**/*.kt")
            targetExclude("**/ui/theme/**", "**/MainActivity.kt", "**/ExampleUnitTest.kt", "**/ExampleInstrumentedTest.kt")
            // Compose 约定 Composable 函数名大写开头，和 ktlint 默认的函数命名规则冲突（同批次2 detekt 的处理）
            ktlint().editorConfigOverride(mapOf("ktlint_function_naming_ignore_when_annotated_with" to "Composable"))
            trimTrailingWhitespace()
            endWithNewline()
        }
        kotlinGradle {
            target("*.gradle.kts")
            ktlint()
        }
    }
}