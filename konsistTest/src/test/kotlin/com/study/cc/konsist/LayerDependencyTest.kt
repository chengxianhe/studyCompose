package com.study.cc.konsist

import com.lemonappdev.konsist.api.Konsist
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 分层依赖规则（对应 docs/compose-ai-bootstrap-final.md 规则1-5）。
 *
 * 这些依赖大多已经由 Gradle 模块的 build.gradle.kts 在编译期强制（模块不在依赖图上，
 * 根本 import 不到），这里再断言一层是防止有人后续悄悄改动 build.gradle.kts 松绑依赖。
 */
class LayerDependencyTest {
    // konsistTest 自身只是测试harness，不是业务模块，排除在架构扫描之外。
    private val allFiles =
        Konsist
            .scopeFromProject()
            .files
            .filterNot { it.path.contains("/konsistTest/") }

    @Test
    fun `domain 模块不依赖任何其他模块或 Android`() {
        val violations =
            allFiles
                .filter { it.path.contains("/domain/") }
                .filter { file ->
                    file.imports.any { import ->
                        import.name.startsWith("android.") ||
                            import.name.startsWith("androidx.") ||
                            import.name.contains(".data.") ||
                            import.name.contains(".feature.") ||
                            import.name.contains(".core.")
                    }
                }
        assertTrue(
            "domain 模块出现了对其他模块/Android 的依赖: ${violations.map { it.path }}",
            violations.isEmpty(),
        )
    }

    @Test
    fun `feature 包禁止 import data 包`() {
        val violations =
            allFiles
                .filter { it.path.contains("/feature/") }
                .filter { file -> file.imports.any { it.name.contains(".data.") } }
        assertTrue(
            "feature 模块出现了对 data 包的 import: ${violations.map { it.path }}",
            violations.isEmpty(),
        )
    }

    @Test
    fun `feature 包之间禁止互相 import`() {
        val featurePackageRegex = Regex("""com\.study\.cc\.feature\.(\w+)""")
        val violations =
            allFiles
                .filter { it.path.contains("/feature/") }
                .filter { file ->
                    val ownFeature = featurePackageRegex.find(file.path.replace('/', '.'))?.groupValues?.get(1)
                    file.imports.any { import ->
                        val importedFeature = featurePackageRegex.find(import.name)?.groupValues?.get(1)
                        importedFeature != null && importedFeature != ownFeature
                    }
                }
        assertTrue(
            "feature 模块之间出现了互相 import: ${violations.map { it.path }}",
            violations.isEmpty(),
        )
    }

    @Test
    fun `domain 包禁止出现 android 或 androidx import`() {
        val violations =
            allFiles
                .filter { it.path.contains("/domain/") }
                .filter { file ->
                    file.imports.any { it.name.startsWith("android.") || it.name.startsWith("androidx.") }
                }
        assertTrue(
            "domain 模块出现了 android/androidx import: ${violations.map { it.path }}",
            violations.isEmpty(),
        )
    }

    @Test
    fun `禁止直接 import android util Log（core logging 除外）`() {
        val violations =
            allFiles
                .filterNot { it.path.contains("/core/logging/") }
                .filter { file -> file.imports.any { it.name == "android.util.Log" } }
        assertTrue(
            "以下文件直接 import 了 android.util.Log，应改用 core:logging 的 Logger: ${violations.map { it.path }}",
            violations.isEmpty(),
        )
    }
}
