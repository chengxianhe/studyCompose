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
}