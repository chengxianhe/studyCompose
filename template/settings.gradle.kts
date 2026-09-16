pluginManagement {
    includeBuild("build-logic")
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "studyCompose"

// :app 不在这里——用 Android Studio 建好 :app 后手动 include，
// 参照 template/README.md 把它接上下面这些模块和 build-logic 约定插件。
include(":domain")
include(":data")
include(":core:common")
include(":core:logging")
include(":core:designsystem")
include(":core:ui")
include(":feature:home")
include(":konsistTest")
 