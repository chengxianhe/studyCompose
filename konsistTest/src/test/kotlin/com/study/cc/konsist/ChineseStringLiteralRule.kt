package com.study.cc.konsist

import org.jetbrains.kotlin.lexer.KotlinLexer
import org.jetbrains.kotlin.lexer.KtTokens

private val chineseText = Regex("[一-龥]")
private val unicodeEscape = Regex("""\\u([0-9a-fA-F]{4})""")

internal fun containsChineseStringLiteral(source: String): Boolean {
    val lexer = KotlinLexer()
    lexer.start(source)
    while (lexer.tokenType != null) {
        val token = lexer.tokenText
        val literal = when (lexer.tokenType) {
            KtTokens.REGULAR_STRING_PART -> token
            KtTokens.ESCAPE_SEQUENCE -> unicodeEscape.matchEntire(token)
                ?.groupValues?.get(1)?.toInt(radix = 16)?.toChar()?.toString().orEmpty()
            else -> ""
        }
        if (chineseText.containsMatchIn(literal)) return true
        lexer.advance()
    }
    return false
}
