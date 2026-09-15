package studycompose.convention

import com.android.build.api.dsl.ApplicationExtension
import com.android.build.api.dsl.CommonExtension
import com.android.build.api.dsl.LibraryExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.configure

class AndroidLintConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            pluginManager.withPlugin("com.android.application") {
                extensions.configure<ApplicationExtension> { configureLint() }
            }
            pluginManager.withPlugin("com.android.library") {
                extensions.configure<LibraryExtension> { configureLint() }
            }
        }
    }
}

private fun CommonExtension<*, *, *, *, *, *>.configureLint() {
    lint {
        abortOnError = true
        checkDependencies = true
        xmlReport = true
    }
}
