package com.study.cc.feature.library

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.setProgress
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.Dp
import com.study.cc.core.designsystem.theme.Sizes
import com.study.cc.domain.model.PhotoDayBucket
import kotlin.math.roundToInt

/** A right-side vertical control whose position represents a day-bucket index, not a photo index. */
@Composable
internal fun DateScrubber(
    buckets: List<PhotoDayBucket>,
    selectedIndex: Int,
    onSelectIndex: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    if (buckets.size < 2) return
    val index = selectedIndex.coerceIn(buckets.indices)
    val current = buckets[index].day
    val label = if (current.isUnknown) {
        stringResource(R.string.library_date_scrubber_unknown)
    } else {
        stringResource(R.string.library_date_scrubber_day, current.year, current.month, current.day)
    }
    val description = stringResource(R.string.library_date_scrubber_label)
    val lastIndex = buckets.lastIndex
    BoxWithConstraints(
        modifier = modifier
            .width(Sizes.minTouchTarget)
            .fillMaxHeight()
            .scrubberInput(lastIndex, onSelectIndex)
            .semantics {
                contentDescription = description
                stateDescription = label
                progressBarRangeInfo = ProgressBarRangeInfo(index.toFloat(), 0f..lastIndex.toFloat())
                setProgress { target ->
                    onSelectIndex(target.roundToInt().coerceIn(0, lastIndex))
                    true
                }
            },
    ) {
        val thumbOffset = (maxHeight - Sizes.dateScrubberThumbSize) * (index.toFloat() / lastIndex)
        ScrubberTrack(thumbOffset)
    }
}

@Composable
private fun BoxScope.ScrubberTrack(thumbOffset: Dp) {
    Box(
        modifier = Modifier
            .align(Alignment.Center)
            .width(Sizes.dateScrubberTrackWidth)
            .fillMaxHeight()
            .background(MaterialTheme.colorScheme.outlineVariant),
    )
    Box(
        modifier = Modifier
            .align(Alignment.TopCenter)
            .offset(y = thumbOffset)
            .size(Sizes.dateScrubberThumbSize)
            .background(MaterialTheme.colorScheme.primary, CircleShape),
    )
}

@Composable
private fun Modifier.scrubberInput(lastIndex: Int, onSelectIndex: (Int) -> Unit): Modifier {
    val selectIndex by rememberUpdatedState(onSelectIndex)
    return pointerInput(lastIndex) {
        detectTapGestures { offset -> selectIndex(indexAt(offset.y, size.height, lastIndex)) }
    }.pointerInput(lastIndex) {
        detectDragGestures(
            onDragStart = { offset -> selectIndex(indexAt(offset.y, size.height, lastIndex)) },
            onDrag = { change, _ ->
                selectIndex(indexAt(change.position.y, size.height, lastIndex))
                change.consume()
            },
        )
    }
}

private fun indexAt(y: Float, height: Int, lastIndex: Int): Int =
    ((y / height.coerceAtLeast(1)) * lastIndex).roundToInt().coerceIn(0, lastIndex)
