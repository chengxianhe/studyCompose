plugins {
    `kotlin-dsl`
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}

dependencies {
    compileOnly(libs.android.gradlePlugin)
    compileOnly(libs.kotlin.gradlePlugin)
    compileOnly(libs.compose.gradlePlugin)
    compileOnly(libs.ksp.gradlePlugin)
    compileOnly(libs.room.gradlePlugin)
    compileOnly(libs.hilt.gradlePlugin)
}

gradlePlugin {
    plugins {
        register("androidApplication") {
            id = "studycompose.android.application"
            implementationClass = "studycompose.convention.AndroidApplicationConventionPlugin"
        }
        register("androidApplicationCompose") {
            id = "studycompose.android.application.compose"
            implementationClass = "studycompose.convention.AndroidApplicationComposeConventionPlugin"
        }
        register("androidLibrary") {
            id = "studycompose.android.library"
            implementationClass = "studycompose.convention.AndroidLibraryConventionPlugin"
        }
        register("androidLibraryCompose") {
            id = "studycompose.android.library.compose"
            implementationClass = "studycompose.convention.AndroidLibraryComposeConventionPlugin"
        }
        register("androidFeature") {
            id = "studycompose.android.feature"
            implementationClass = "studycompose.convention.AndroidFeatureConventionPlugin"
        }
        register("androidRoom") {
            id = "studycompose.android.room"
            implementationClass = "studycompose.convention.AndroidRoomConventionPlugin"
        }
        register("jvmLibrary") {
            id = "studycompose.jvm.library"
            implementationClass = "studycompose.convention.JvmLibraryConventionPlugin"
        }
        register("hilt") {
            id = "studycompose.hilt"
            implementationClass = "studycompose.convention.HiltConventionPlugin"
        }
        register("androidLint") {
            id = "studycompose.android.lint"
            implementationClass = "studycompose.convention.AndroidLintConventionPlugin"
        }
    }
}
