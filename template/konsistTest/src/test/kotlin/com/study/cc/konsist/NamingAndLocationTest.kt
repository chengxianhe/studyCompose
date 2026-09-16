package com.study.cc.konsist

import com.lemonappdev.konsist.api.Konsist
import com.lemonappdev.konsist.api.verify.assertTrue
import org.junit.Test

/** 命名与位置规则（规则6-10）。目前业务代码还是空骨架，多数断言在空集合上恒真，等真实类出现才生效。 */
class NamingAndLocationTest {
    @Test
    fun `继承 ViewModel 的类必须以 ViewModel 结尾`() {
        Konsist
            .scopeFromProject()
            .classes()
            .filter { it.hasParentWithName("ViewModel") }
            .assertTrue { it.hasNameEndingWith("ViewModel") }
    }

    @Test
    fun `UseCase 后缀的类必须在 usecase 包下且只有一个 public 方法`() {
        Konsist
            .scopeFromProject()
            .classes()
            .filter { it.hasNameEndingWith("UseCase") }
            .assertTrue { useCase ->
                useCase.resideInPackage("..domain.usecase..") &&
                    useCase.functions().count { it.hasPublicOrDefaultModifier } == 1
            }
    }

    @Test
    fun `Repository 接口必须在 domain repository 包下`() {
        Konsist
            .scopeFromProject()
            .interfaces()
            .filter { it.hasNameEndingWith("Repository") }
            .assertTrue { it.resideInPackage("..domain.repository..") }
    }

    @Test
    fun `Repository 实现必须在 data repository 包下且以 Impl 结尾`() {
        Konsist
            .scopeFromProject()
            .classes()
            .filter { it.hasParentWithName("Repository") }
            .assertTrue { it.hasNameEndingWith("RepositoryImpl") && it.resideInPackage("..data.repository..") }
    }

    @Test
    fun `Dto 后缀的类必须在 data 包下`() {
        Konsist
            .scopeFromProject()
            .classes()
            .filter { it.hasNameEndingWith("Dto") }
            .assertTrue { it.resideInPackage("..data..") }
    }

    @Test
    fun `Composable 函数名必须大写开头`() {
        Konsist
            .scopeFromProject()
            .functions()
            .filter { it.hasAnnotationWithName("Composable") }
            .assertTrue { it.name.firstOrNull()?.isUpperCase() == true }
    }
}
