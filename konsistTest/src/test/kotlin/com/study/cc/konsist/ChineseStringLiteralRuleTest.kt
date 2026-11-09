package com.study.cc.konsist

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChineseStringLiteralRuleTest {
    @Test
    fun `comments between strings are not user text`() {
        assertFalse(containsChineseStringLiteral("val a = \"one\"\n// 日期分桶\nval b = \"two\""))
        assertFalse(containsChineseStringLiteral("val a = \"one\"\n/* 日期\n分桶 */\nval b = \"two\""))
    }

    @Test
    fun `ordinary and escaped quote literals remain forbidden`() {
        assertTrue(containsChineseStringLiteral("val a = \"照片\""))
        assertTrue(containsChineseStringLiteral("val a = \"say \\\"照片\\\"\""))
        assertFalse(containsChineseStringLiteral("val a = \"photo\""))
    }

    @Test
    fun `raw multiline strings preserve comment markers as literal text`() {
        assertTrue(containsChineseStringLiteral("val a = \"\"\"first\n// 照片\n\"\"\""))
        assertTrue(containsChineseStringLiteral("val a = \"\"\"/* 照片 */\"\"\""))
    }

    @Test
    fun `templates check literal and nested string segments but ignore expression comments`() {
        assertTrue(containsChineseStringLiteral("val a = \"照片 ${'$'}count\""))
        assertTrue(containsChineseStringLiteral("val a = \"${'$'}{format(\"照片\")}\""))
        assertFalse(containsChineseStringLiteral("val a = \"${'$'}{ /* 日期 */ value }\""))
        assertFalse(containsChineseStringLiteral("val a = \"${'$'}{value // 日期\n}\""))
    }

    @Test
    fun `unicode escapes are decoded only in escaped strings`() {
        assertTrue(containsChineseStringLiteral("val a = \"\\u4e2d\""))
        assertFalse(containsChineseStringLiteral("val a = \"\\\\u4e2d\""))
        assertFalse(containsChineseStringLiteral("val a = \"\"\"\\u4e2d\"\"\""))
    }
}
