package com.study.cc.benchmark

import androidx.benchmark.macro.CompilationMode
import androidx.benchmark.macro.FrameTimingMetric
import androidx.benchmark.macro.StartupMode
import androidx.benchmark.macro.junit4.MacrobenchmarkRule
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Direction
import com.study.cc.benchmark.BenchmarkTarget.configure
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.runners.Parameterized

private const val ITERATIONS = 5
private const val FLINGS_PER_ITERATION = 8
private const val GESTURE_MARGIN = 100
private const val GRID_TIMEOUT_MS = 30_000L

/** 在占位网格上连续向下 fling，度量帧耗时与卡顿帧。 */
@RunWith(Parameterized::class)
class ScrollBenchmark(private val scale: Int) {
    @get:Rule
    val rule = MacrobenchmarkRule()

    @Test
    fun flingDown() {
        BenchmarkTarget.ensureSeeded(scale)
        rule.measureRepeated(
            packageName = BenchmarkTarget.PACKAGE,
            metrics = listOf(FrameTimingMetric()),
            iterations = ITERATIONS,
            startupMode = StartupMode.WARM,
            compilationMode = CompilationMode.DEFAULT,
            setupBlock = {
                pressHome()
                startActivityAndWait { it.configure(BenchmarkTarget.MODE_GRID, scale) }
            },
        ) {
            val grid = device.wait(
                androidx.test.uiautomator.Until.findObject(
                    By.res(BenchmarkTarget.GRID_TAG),
                ),
                GRID_TIMEOUT_MS,
            ) ?: error("grid not found")
            grid.setGestureMargin(GESTURE_MARGIN)
            repeat(FLINGS_PER_ITERATION) {
                grid.fling(Direction.DOWN)
                device.waitForIdle()
            }
        }
    }

    companion object {
        @JvmStatic
        @Parameterized.Parameters(name = "scale={0}")
        fun scales(): List<Int> = BenchmarkTarget.scales()
    }
}
