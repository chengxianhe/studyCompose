package com.study.cc.core.designsystem.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

// ① 基础层 —— internal，外部无法访问，只能被本文件内的语义层引用
internal val Blue50 = Color(0xFFE6F1FB)
internal val Blue500 = Color(0xFF3366FF)
internal val Blue900 = Color(0xFF042C53)
internal val Neutral0 = Color(0xFFFFFFFF)
internal val Neutral50 = Color(0xFFF5F5F5)
internal val Neutral200 = Color(0xFFE0E0E0)
internal val Neutral500 = Color(0xFF757575)
internal val Neutral800 = Color(0xFF2B2B2B)
internal val Neutral900 = Color(0xFF1A1A1A)
internal val Red500 = Color(0xFFD32F2F)
internal val Red900 = Color(0xFF5F0000)
internal val Green500 = Color(0xFF2E7D32)
internal val Amber500 = Color(0xFFF9A825)

// ② 语义层 —— Material3 colorScheme，业务代码只能通过 MaterialTheme.colorScheme 使用
internal val LightColors = lightColorScheme(
    primary = Blue500,
    onPrimary = Neutral0,
    primaryContainer = Blue50,
    onPrimaryContainer = Blue900,
    surface = Neutral0,
    onSurface = Neutral900,
    surfaceVariant = Neutral50,
    onSurfaceVariant = Neutral500,
    outline = Neutral200,
    error = Red500,
    onError = Neutral0,
)

internal val DarkColors = darkColorScheme(
    primary = Blue50,
    onPrimary = Blue900,
    primaryContainer = Blue900,
    onPrimaryContainer = Blue50,
    surface = Neutral900,
    onSurface = Neutral0,
    surfaceVariant = Neutral800,
    onSurfaceVariant = Neutral200,
    outline = Neutral500,
    error = Red500,
    onError = Neutral900,
)

@Immutable
data class ExtendedColors(
    val success: Color,
    val onSuccess: Color,
    val warning: Color,
    val onWarning: Color,
)

internal val LightExtendedColors = ExtendedColors(
    success = Green500,
    onSuccess = Neutral0,
    warning = Amber500,
    onWarning = Neutral900,
)

internal val DarkExtendedColors = ExtendedColors(
    success = Green500,
    onSuccess = Neutral900,
    warning = Amber500,
    onWarning = Neutral900,
)

val LocalExtendedColors = staticCompositionLocalOf { LightExtendedColors }
