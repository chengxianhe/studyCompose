package com.study.cc.benchmark

import androidx.benchmark.macro.CompilationMode
import androidx.benchmark.macro.StartupMode
import androidx.benchmark.macro.StartupTimingMetric
import androidx.benchmark.macro.junit4.MacrobenchmarkRule
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import com.study.cc.benchmark.BenchmarkTarget.configure
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.runners.Parameterized

private const val ITERATIONS = 5
private const val CONTENT_TIMEOUT_MS = 30_000L
private const val FRAME_SETTLE_MS = 1_000L

/** 冷启动到首屏内容（TTFD：被测 App 在日桶加载完成后调用 reportFullyDrawn）。 */
@RunWith(Parameterized::class)
class ColdStartBenchmark(private val scale: Int) {
    @get:Rule
    val rule = MacrobenchmarkRule()

    @Test
    fun coldStart() {
        BenchmarkTarget.ensureSeeded(scale)
        rule.measureRepeated(
            packageName = BenchmarkTarget.PACKAGE,
            metrics = listOf(StartupTimingMetric()),
            iterations = ITERATIONS,
            startupMode = StartupMode.COLD,
            compilationMode = CompilationMode.DEFAULT,
        ) {
            pressHome()
            startActivityAndWait { it.configure(BenchmarkTarget.MODE_GRID, scale) }
            // startActivityAndWait 在首帧就返回；要录到 reportFullyDrawn（首屏内容就绪）必须继续等到网格出现
            device.wait(Until.hasObject(By.res(BenchmarkTarget.GRID_TAG)), CONTENT_TIMEOUT_MS)
            device.waitForIdle()
            // 再留出时间让 reportFullyDrawn 之后至少渲染一帧，否则 Macrobenchmark 找不到对应的渲染帧会报错
            Thread.sleep(FRAME_SETTLE_MS)
        }
    }

    companion object {
        @JvmStatic
        @Parameterized.Parameters(name = "scale={0}")
        fun scales(): List<Int> = BenchmarkTarget.scales()
    }
}
