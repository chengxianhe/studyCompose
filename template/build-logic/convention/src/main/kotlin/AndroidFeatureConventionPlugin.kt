package studycompose.convention

import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.dependencies

class AndroidFeatureConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            pluginManager.apply("studycompose.android.library")
            pluginManager.apply("studycompose.android.library.compose")
            pluginManager.apply("studycompose.hilt")

            dependencies {
                add("implementation", project(":domain"))
                add("implementation", project(":core:common"))
                add("implementation", project(":core:logging"))
                add("implementation", project(":core:designsystem"))
                add("implementation", project(":core:ui"))

                add("implementation", libs.findLibrary("kotlinx-coroutines-android").get())
                add("implementation", libs.findLibrary("androidx-lifecycle-runtime-ktx").get())
            }
        }
    }
}
