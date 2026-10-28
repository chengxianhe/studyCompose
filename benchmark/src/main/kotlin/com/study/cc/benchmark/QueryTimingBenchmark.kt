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

private const val ITERATIONS = 5
private const val MARKER_TIMEOUT_MS = 120_000L

/** 各条产品查询的耗时，以及不预存本地日列（strftime 现算）的对照。 */
@OptIn(ExperimentalMetricApi::class)
@RunWith(Parameterized::class)
class QueryTimingBenchmark(private val scale: Int) {
    @get:Rule
    val rule = MacrobenchmarkRule()

    @Test
    fun queries() {
        rule.measureRepeated(
            packageName = BenchmarkTarget.PACKAGE,
            metrics = BenchmarkTarget.QUERY_TRACES.map { TraceSectionMetric(it) },
            iterations = ITERATIONS,
            startupMode = StartupMode.COLD,
            compilationMode = CompilationMode.DEFAULT,
            setupBlock = { BenchmarkTarget.ensureSeeded(scale) },
        ) {
            pressHome()
            startActivityAndWait { it.configure(BenchmarkTarget.MODE_QUERIES, scale) }
            BenchmarkTarget.waitForMarker(device, BenchmarkTarget.MARKER_QUERIES_DONE, MARKER_TIMEOUT_MS)
        }
    }

    @Test
    fun loadAllIntoLongArrays() {
        rule.measureRepeated(
            packageName = BenchmarkTarget.PACKAGE,
            metrics = listOf(TraceSectionMetric(BenchmarkTarget.TRACE_LONG_ARRAYS)),
            iterations = ITERATIONS,
            startupMode = StartupMode.COLD,
            compilationMode = CompilationMode.DEFAULT,
            setupBlock = { BenchmarkTarget.ensureSeeded(scale) },
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
