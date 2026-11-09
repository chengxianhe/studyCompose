package com.study.cc.feature.library

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyGridScope
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import coil.ImageLoader
import com.study.cc.core.designsystem.theme.Sizes
import com.study.cc.core.designsystem.theme.Spacing
import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoDayBucket
import com.study.cc.domain.model.PhotoMedia
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

@Composable
internal fun PhotoDayGrid(
    buckets: List<PhotoDayBucket>,
    itemsByDay: Map<PhotoDay, List<PhotoMedia>>,
    imageLoader: ImageLoader,
    onDaysVisible: (Set<PhotoDay>) -> Unit,
    modifier: Modifier = Modifier,
) {
    val state = rememberLazyGridState()
    val layout = remember(buckets) { PhotoDayGridLayout(buckets) }
    val selectedIndex by remember(layout, state) {
        derivedStateOf { layout.bucketIndexOf(state.firstVisibleItemIndex) }
    }
    val scope = rememberCoroutineScope()
    var jump by remember { mutableStateOf<Job?>(null) }
    PhotoDayViewport(state, layout, buckets, onDaysVisible)
    Row(modifier = modifier.fillMaxSize()) {
        LazyVerticalGrid(
            columns = GridCells.Fixed(Sizes.PHOTO_GRID_COLUMN_COUNT),
            state = state,
            horizontalArrangement = Arrangement.spacedBy(Spacing.photoGridGap),
            verticalArrangement = Arrangement.spacedBy(Spacing.photoGridGap),
            modifier = Modifier.weight(1f),
        ) {
            dayItems(buckets, itemsByDay, imageLoader)
        }
        DateScrubber(buckets, selectedIndex, onSelectIndex = { index ->
            jump?.cancel()
            jump = scope.launch { state.scrollToItem(layout.startIndexOf(index)) }
        })
    }
}

private fun LazyGridScope.dayItems(
    buckets: List<PhotoDayBucket>,
    itemsByDay: Map<PhotoDay, List<PhotoMedia>>,
    imageLoader: ImageLoader,
) {
    buckets.forEach { bucket ->
        val day = bucket.day
        val key = "${day.year}-${day.month}-${day.day}"
        stickyHeader(key = "header:$key", contentType = "day") { PhotoDayHeader(bucket) }
        items(count = bucket.total, key = { "photo:$key:$it" }, contentType = { "photo" }) { index ->
            PhotoTile(itemsByDay[day]?.getOrNull(index), imageLoader, Modifier.aspectRatio(1f))
        }
    }
}
