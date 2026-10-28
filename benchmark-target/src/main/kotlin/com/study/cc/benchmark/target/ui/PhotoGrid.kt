package com.study.cc.benchmark.target.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import com.study.cc.benchmark.target.R
import com.study.cc.core.designsystem.theme.Spacing

const val GRID_TAG = "photo_grid"
private const val COLUMNS = 4
private const val CONTENT_HEADER = 0
private const val CONTENT_CELL = 1

/** 占位网格：纯色格子，不加载缩略图——只度量「数据路径 + 布局」，解码开销留给 T-014 实机图。 */
@Composable
fun PhotoGrid(layout: DayGridLayout, cache: DayIdsCache, modifier: Modifier = Modifier) {
    LazyVerticalGrid(
        columns = GridCells.Fixed(COLUMNS),
        modifier = modifier
            .fillMaxSize()
            .testTag(GRID_TAG),
    ) {
        items(
            count = layout.itemCount,
            span = { item -> GridItemSpan(if (layout.isHeader(item)) COLUMNS else 1) },
            contentType = { item -> if (layout.isHeader(item)) CONTENT_HEADER else CONTENT_CELL },
        ) { item ->
            val bucketIndex = layout.bucketIndexOf(item)
            if (layout.isHeader(item)) {
                DayHeader(layout.bucket(bucketIndex))
            } else {
                PlaceholderCell(bucketIndex, cache)
            }
        }
    }
}

@Composable
private fun DayHeader(bucket: com.study.cc.benchmark.target.store.DayBucket) {
    val text =
        if (bucket.year == 0) {
            stringResource(R.string.bench_unknown_header, bucket.total)
        } else {
            stringResource(R.string.bench_day_header, bucket.year, bucket.month, bucket.day, bucket.total)
        }
    Text(
        text = text,
        style = MaterialTheme.typography.titleSmall,
        modifier = Modifier.padding(Spacing.sm),
    )
}

@Composable
private fun PlaceholderCell(bucketIndex: Int, cache: DayIdsCache) {
    val ids = cache.idsFor(bucketIndex)
    if (ids == null) LaunchedEffect(bucketIndex) { cache.ensureLoaded(bucketIndex) }
    val color =
        if (ids == null) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.secondaryContainer
    Box(
        modifier = Modifier
            .padding(Spacing.xxs)
            .aspectRatio(1f)
            .background(color),
    )
}
