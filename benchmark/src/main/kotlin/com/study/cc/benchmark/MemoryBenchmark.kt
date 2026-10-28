package com.study.cc.benchmark

import androidx.benchmark.macro.CompilationMode
import androidx.benchmark.macro.ExperimentalMetricApi
import androidx.benchmark.macro.MemoryUsageMetric
import androidx.benchmark.macro.StartupMode
import androidx.benchmark.macro.junit4.MacrobenchmarkRule
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Direction
import androidx.test.uiautomator.Until
import com.study.cc.benchmark.BenchmarkTarget.configure
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.runners.Parameterized

private const val ITERATIONS = 3
private const val FLINGS = 8
private const val GRID_TIMEOUT_MS = 30_000L
private const val MARKER_TIMEOUT_MS = 120_000L

/** 内存峰值：占位网格滚动 vs 把全部 id + 时间读进 LongArray 的反例，两者放在一起对照。 */
@OptIn(ExperimentalMetricApi::class)
@RunWith(Parameterized::class)
class MemoryBenchmark(private val scale: Int) {
    @get:Rule
    val rule = MacrobenchmarkRule()

    @Test
    fun gridMemory() {
        BenchmarkTarget.ensureSeeded(scale)
        rule.measureRepeated(
            packageName = BenchmarkTarget.PACKAGE,
            metrics = listOf(MemoryUsageMetric(MemoryUsageMetric.Mode.Max)),
            iterations = ITERATIONS,
            startupMode = StartupMode.COLD,
            compilationMode = CompilationMode.DEFAULT,
        ) {
            pressHome()
            startActivityAndWait { it.configure(BenchmarkTarget.MODE_GRID, scale) }
            val grid =
                device.wait(
                    Until.findObject(By.res(BenchmarkTarget.GRID_TAG)),
                    GRID_TIMEOUT_MS,
                )
                    ?: error("grid not found")
            repeat(FLINGS) {
                grid.fling(Direction.DOWN)
                device.waitForIdle()
            }
        }
    }

    @Test
    fun longArraysMemory() {
        BenchmarkTarget.ensureSeeded(scale)
        rule.measureRepeated(
            packageName = BenchmarkTarget.PACKAGE,
            metrics = listOf(MemoryUsageMetric(MemoryUsageMetric.Mode.Max)),
            iterations = ITERATIONS,
            startupMode = StartupMode.COLD,
            compilationMode = CompilationMode.DEFAULT,
        ) {
            pressHome()
            startActivityAndWait { it.configure(BenchmarkTarget.MODE_LONG_ARRAYS, scale) }
            BenchmarkTarget.waitForMarker(device, BenchmarkTarget.MARKER_LONG_ARRAYS_DONE, MARKER_TIMEOUT_MS)
        }
    }

    companion object {
        @JvmStatic
        @Parameterized.Parameters(name = "scale={0}")
        fun scales(): List<Int> = BenchmarkTarget.scales()
    }
}
