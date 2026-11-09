package com.study.cc.feature.library

import androidx.compose.foundation.lazy.grid.LazyGridState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.snapshotFlow
import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoDayBucket
import kotlinx.coroutines.flow.distinctUntilChanged

/** Query visible buckets only; dispose cancels requests when the grid leaves composition. */
@Composable
internal fun PhotoDayViewport(
    state: LazyGridState,
    layout: PhotoDayGridLayout,
    buckets: List<PhotoDayBucket>,
    onDaysVisible: (Set<PhotoDay>) -> Unit,
) {
    val notifyVisible by rememberUpdatedState(onDaysVisible)
    LaunchedEffect(state, layout) {
        snapshotFlow {
            state.layoutInfo.visibleItemsInfo
                .filter { it.index in 0 until layout.itemCount }
                .map { buckets[layout.bucketIndexOf(it.index)].day }
                .toSet()
        }.distinctUntilChanged().collect { notifyVisible(it) }
    }
    DisposableEffect(Unit) {
        onDispose { notifyVisible(emptySet()) }
    }
}
