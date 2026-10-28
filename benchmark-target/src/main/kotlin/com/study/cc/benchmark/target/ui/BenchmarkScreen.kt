package com.study.cc.benchmark.target.ui

import android.content.Context
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import com.study.cc.benchmark.target.R
import com.study.cc.benchmark.target.probe.BenchMode
import com.study.cc.benchmark.target.probe.QueryProbe
import com.study.cc.benchmark.target.probe.TraceNames
import com.study.cc.benchmark.target.probe.traced
import com.study.cc.benchmark.target.store.BenchmarkDatabase
import com.study.cc.benchmark.target.store.GeneratorConfig
import com.study.cc.benchmark.target.store.PhotoSeeder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** 一次运行的结果：要么是一个状态文案资源（非网格模式），要么是可显示的网格。 */
private sealed interface Outcome {
    data class Status(val messageRes: Int) : Outcome

    class Grid(val layout: DayGridLayout, val cache: DayIdsCache) : Outcome
}

@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun BenchmarkScreen(mode: BenchMode, scale: Int, onReady: () -> Unit, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val outcome by produceState<Outcome?>(initialValue = null, mode, scale) {
        value = withContext(Dispatchers.IO) { runMode(context, mode, scale) }
    }
    LaunchedEffect(outcome) { if (outcome != null) onReady() }
    Box(
        modifier = modifier
            .fillMaxSize()
            // UiAutomator 通过 resource-id 找到 testTag；放在祖先节点上对整棵子树生效
            .semantics { testTagsAsResourceId = true },
        contentAlignment = Alignment.Center,
    ) {
        when (val current = outcome) {
            null -> Text(text = stringResource(R.string.bench_status_loading))
            is Outcome.Status -> Text(text = stringResource(current.messageRes))
            is Outcome.Grid -> remember(current) { current }.let { PhotoGrid(it.layout, it.cache) }
        }
    }
}

private fun runMode(context: Context, mode: BenchMode, scale: Int): Outcome = runCatching {
    if (mode == BenchMode.RESEED) BenchmarkDatabase.delete(context, scale)
    val database = BenchmarkDatabase.open(context, scale)
    val config = GeneratorConfig(total = scale)
    ensureSeeded(database, config)
    val probe = QueryProbe(database)
    when (mode) {
        BenchMode.SEED, BenchMode.RESEED -> Outcome.Status(R.string.bench_status_seed_done)
        BenchMode.QUERIES -> {
            probe.runAll(config)
            Outcome.Status(R.string.bench_status_queries_done)
        }
        BenchMode.LONG_ARRAYS -> {
            probe.loadAllIntoLongArrays()
            Outcome.Status(R.string.bench_status_long_arrays_done)
        }
        BenchMode.GRID -> {
            val layout = DayGridLayout(probe.dayBuckets())
            Outcome.Grid(layout, DayIdsCache(database.photoMetaDao(), layout))
        }
    }
}.getOrElse { Outcome.Status(R.string.bench_status_error) }

private fun ensureSeeded(database: BenchmarkDatabase, config: GeneratorConfig) {
    val existing = database.photoMetaDao().count()
    // 排查「首次迭代重新灌库」：把启动时库里的行数写进 trace 段名，事后可在 Perfetto 里查
    traced("bench.existingRows=$existing/${config.total}") { }
    if (existing == config.total) return
    // 上次灌到一半被系统杀掉会留下残缺的库，必须先清空，否则再灌一遍行数永远对不上
    database.clearAllTables()
    traced(TraceNames.SEED) { PhotoSeeder(database).seed(config) }
}
