package com.study.cc.konsist

import com.lemonappdev.konsist.api.Konsist
import org.junit.Assert.assertTrue
import org.junit.Test

/** 数据库规则（规则19）。 */
class DatabaseTest {

    @Test
    fun `禁止调用 fallbackToDestructiveMigration`() {
        val violations = Konsist.scopeFromProject().files
            .filterNot { it.path.contains("/konsistTest/") }
            .filter { it.text.contains("fallbackToDestructiveMigration") }
        assertTrue(
            "以下文件调用了 fallbackToDestructiveMigration，会清空用户数据，请改写 Migration: ${violations.map { it.path }}",
            violations.isEmpty(),
        )
    }
}
