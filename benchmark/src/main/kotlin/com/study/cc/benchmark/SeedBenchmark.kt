package com.study.cc.benchmark

import androidx.benchmark.macro.CompilationMode
import androidx.benchmark.macro.ExperimentalMetricApi
import androidx.benchmark.macro.StartupMode
import androidx.benchmark.macro.TraceSectionMetric
import androidx.benchmark.macro.junit4.MacrobenchmarkRule
import com.study.cc.benchmark.BenchmarkTarget.configure
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.runners.Parameterized

private const val SEED_TIMEOUT_MS = 15 * 60 * 1000L

/** 首次全量灌入耗时（先删库再生成），是 T-012 首次同步预算的参照。每个规模只跑一次。 */
@OptIn(ExperimentalMetricApi::class)
@RunWith(Parameterized::class)
class SeedBenchmark(private val scale: Int) {
    @get:Rule
    val rule = MacrobenchmarkRule()

    @Test
    fun seedFromScratch() {
        rule.measureRepeated(
            packageName = BenchmarkTarget.PACKAGE,
            metrics = listOf(TraceSectionMetric(BenchmarkTarget.TRACE_SEED, TraceSectionMetric.Mode.First)),
            iterations = 1,
            startupMode = StartupMode.COLD,
            compilationMode = CompilationMode.DEFAULT,
        ) {
            pressHome()
            startActivityAndWait { it.configure(BenchmarkTarget.MODE_RESEED, scale) }
            BenchmarkTarget.waitForMarker(device, BenchmarkTarget.MARKER_SEED_DONE, SEED_TIMEOUT_MS)
        }
    }

    companion object {
        @JvmStatic
        @Parameterized.Parameters(name = "scale={0}")
        fun scales(): List<Int> = BenchmarkTarget.scales()
    }
}
