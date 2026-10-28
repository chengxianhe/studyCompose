package studycompose.convention

import com.android.build.api.dsl.TestExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.configure

class AndroidTestConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            pluginManager.apply("com.android.test")
            pluginManager.apply("org.jetbrains.kotlin.android")

            extensions.configure<TestExtension> {
                defaultConfig.targetSdk = 36
                configureKotlinAndroid(this)
            }
        }
    }
}
