package com.study.cc.benchmark

import android.content.Intent
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until

/** 与 :benchmark-target 约定的常量；改动时两边要同步（见其 BenchMode / strings.xml）。 */
internal object BenchmarkTarget {
    const val PACKAGE = "com.study.cc.benchmark.target"
    const val GRID_TAG = "photo_grid"
    const val EXTRA_MODE = "mode"
    const val EXTRA_SCALE = "scale"

    const val MODE_SEED = "seed"
    const val MODE_RESEED = "reseed"
    const val MODE_GRID = "grid"
    const val MODE_QUERIES = "queries"
    const val MODE_LONG_ARRAYS = "longarrays"

    const val MARKER_SEED_DONE = "seed-done"
    const val MARKER_QUERIES_DONE = "queries-done"
    const val MARKER_LONG_ARRAYS_DONE = "long-arrays-done"

    const val TRACE_SEED = "bench.seed"
    val QUERY_TRACES =
        listOf(
            "q.yearSummaries",
            "q.monthSummaries",
            "q.daySummaries",
            "q.dayBuckets",
            "q.idsOfDay",
            "q.onThisDay",
            "q.yearSummariesViaStrftime",
            "q.upsert1000",
        )
    const val TRACE_LONG_ARRAYS = "q.loadAllIntoLongArrays"

    private const val SEED_TIMEOUT_MS = 15 * 60 * 1000L
    private const val MAX_LAUNCH_ATTEMPTS = 5
    private const val RELAUNCH_DELAY_MS = 2_000L
    private const val POLL_INTERVAL_MS = 1_000L
    private const val SCALE_SMALL = 100_000
    private const val SCALE_MEDIUM = 500_000
    private const val SCALE_TARGET = 1_000_000
    private val DEFAULT_SCALES = listOf(SCALE_SMALL, SCALE_MEDIUM, SCALE_TARGET)

    /** 可用 `-Pandroid.testInstrumentationRunnerArguments.scales=100000,1000000` 只跑部分规模。 */
    fun scales(): List<Int> {
        val argument = InstrumentationRegistry.getArguments().getString("scales")
        return argument?.split(',')?.mapNotNull { it.trim().toIntOrNull() } ?: DEFAULT_SCALES
    }

    fun Intent.configure(mode: String, scale: Int) {
        putExtra(EXTRA_MODE, mode)
        putExtra(EXTRA_SCALE, scale)
    }

    /**
     * 保证某规模的库已生成：跑一次 seed 模式并等到界面出现完成标记；已存在时几乎瞬间返回。
     * 部分厂商 ROM（如 EMUI 的 iAware）会在刚启动后把应用强停，所以进程消失时重新拉起，而不是干等到超时。
     */
    fun ensureSeeded(scale: Int) {
        val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
        repeat(MAX_LAUNCH_ATTEMPTS) {
            device.executeShellCommand("am force-stop $PACKAGE")
            Thread.sleep(RELAUNCH_DELAY_MS)
            device.executeShellCommand(
                "am start -W -n $PACKAGE/$PACKAGE.MainActivity --es $EXTRA_MODE $MODE_SEED --ei $EXTRA_SCALE $scale",
            )
            if (waitWhileAlive(device, SEED_TIMEOUT_MS)) {
                device.executeShellCommand("am force-stop $PACKAGE")
                return
            }
        }
        error("seeding $scale rows did not complete after $MAX_LAUNCH_ATTEMPTS launches")
    }

    /** 等到完成标记返回 true；进程消失或超时返回 false。 */
    private fun waitWhileAlive(device: UiDevice, timeoutMs: Long): Boolean {
        val deadline = System.currentTimeMillis() + timeoutMs
        var done = false
        var alive = true
        while (!done && alive && System.currentTimeMillis() < deadline) {
            done = device.hasObject(By.text(MARKER_SEED_DONE))
            alive = done || device.executeShellCommand("pidof $PACKAGE").isNotBlank()
            if (!done && alive) Thread.sleep(POLL_INTERVAL_MS)
        }
        return done
    }

    fun waitForMarker(device: UiDevice, marker: String, timeoutMs: Long) {
        check(device.wait(Until.hasObject(By.text(marker)), timeoutMs)) { "timed out waiting for '$marker'" }
    }
}
