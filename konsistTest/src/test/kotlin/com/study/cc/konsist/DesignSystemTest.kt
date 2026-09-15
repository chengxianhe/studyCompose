package com.study.cc.konsist

import com.lemonappdev.konsist.api.Konsist
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 设计系统规则（规则15-18，对应 docs/compose-design-system-and-ai-constraints.md 第7.1节）。
 *
 * scope 严格限定 feature/ 和 data/，排除 Preview 文件和测试目录——
 * :core:designsystem 本身就是定义这些值的地方，天然豁免。
 */
class DesignSystemTest {

    private val scopedFiles = Konsist.scopeFromProject().files
        .filter { it.path.contains("/feature/") || it.path.contains("/data/") }
        .filterNot { it.name.endsWith("Preview.kt") }
        .filterNot { it.path.contains("/test/") || it.path.contains("/androidTest/") }

    @Test
    fun `feature data 模块禁止硬编码颜色`() {
        val violations = scopedFiles.filter { it.text.contains(Regex("""Color\(0x[0-9A-Fa-f]{8}\)""")) }
        assertTrue(
            "以下文件存在硬编码颜色，请使用 MaterialTheme.colorScheme 或新增 token: ${violations.map { it.path }}",
            violations.isEmpty(),
        )
    }

    @Test
    fun `feature data 模块禁止内联 dp 数值`() {
        val violations = scopedFiles.mapNotNull { file ->
            val matches = Regex("""(?<![\w.])(\d+)\.dp""").findAll(file.text)
                .map { it.groupValues[1].toInt() }
                .filter { it != 0 && it != 1 }
                .toList()
            if (matches.isNotEmpty()) file.path to matches else null
        }
        assertTrue("以下文件存在内联 dp: $violations", violations.isEmpty())
    }

    @Test
    fun `禁止内联 sp 字号`() {
        val violations = scopedFiles.filter { it.text.contains(Regex("""fontSize\s*=\s*\d+\.sp""")) }
        assertTrue(
            "以下文件存在内联 fontSize，请使用 MaterialTheme.typography: ${violations.map { it.path }}",
            violations.isEmpty(),
        )
    }

    @Test
    fun `禁止硬编码中文字符串`() {
        val violations = scopedFiles.filter { it.text.contains(Regex(""""[^"]*[一-龥]+[^"]*"""")) }
        assertTrue(
            "以下文件存在硬编码中文，请使用 stringResource: ${violations.map { it.path }}",
            violations.isEmpty(),
        )
    }

    @Test
    fun `feature data 模块禁止直接引用设计系统基础色`() {
        val violations = scopedFiles.filter { file ->
            file.imports.any {
                it.name.contains("designsystem.theme.Blue") || it.name.contains("designsystem.theme.Neutral")
            }
        }
        assertTrue(
            "以下文件直接引用了基础色，只能用语义层（MaterialTheme.colorScheme）: ${violations.map { it.path }}",
            violations.isEmpty(),
        )
    }
}
