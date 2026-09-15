package com.study.cc.konsist

import com.lemonappdev.konsist.api.Konsist
import com.lemonappdev.konsist.api.verify.assertTrue
import org.junit.Assert.assertTrue as junitAssertTrue
import org.junit.Test

private const val MAX_FILE_LINES = 250
private const val MAX_VIEWMODEL_PUBLIC_FUNCTIONS = 8

/** 结构规则（规则11-14）。 */
class StructureTest {

    @Test
    fun `ViewModel 的 public 属性只能是 StateFlow`() {
        Konsist.scopeFromProject()
            .classes()
            .filter { it.hasNameEndingWith("ViewModel") }
            .flatMap { it.properties() }
            .filter { it.hasPublicOrDefaultModifier }
            .assertTrue {
                it.hasTacitType("StateFlow") &&
                    !it.hasTacitType("MutableStateFlow") &&
                    !it.hasTacitType("SharedFlow") &&
                    !it.hasTacitType("Channel")
            }
    }

    @Test
    fun `Repository 接口方法返回类型不得是 Response 或 Call`() {
        Konsist.scopeFromProject()
            .interfaces()
            .filter { it.hasNameEndingWith("Repository") }
            .flatMap { it.functions() }
            .assertTrue {
                it.returnType?.hasNameEndingWith("Response") != true &&
                    it.returnType?.hasNameEndingWith("Call") != true
            }
    }

    @Test
    fun `单个文件不超过250行`() {
        val violations = Konsist.scopeFromProject().files
            .filterNot { it.path.contains("/konsistTest/") }
            .filter { it.text.lines().size > MAX_FILE_LINES }
        junitAssertTrue(
            "以下文件超过 $MAX_FILE_LINES 行，请拆分: ${violations.map { it.path }}",
            violations.isEmpty(),
        )
    }

    @Test
    fun `ViewModel public 方法不超过8个`() {
        Konsist.scopeFromProject()
            .classes()
            .filter { it.hasNameEndingWith("ViewModel") }
            .assertTrue { vm ->
                vm.functions().count { it.hasPublicOrDefaultModifier } <= MAX_VIEWMODEL_PUBLIC_FUNCTIONS
            }
    }
}
