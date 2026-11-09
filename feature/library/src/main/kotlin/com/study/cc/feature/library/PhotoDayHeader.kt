package com.study.cc.feature.library

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.study.cc.core.designsystem.theme.Spacing
import com.study.cc.domain.model.PhotoDayBucket

@Composable
internal fun PhotoDayHeader(bucket: PhotoDayBucket) {
    val day = bucket.day
    val label = if (day.isUnknown) {
        stringResource(R.string.library_day_unknown_header, bucket.total)
    } else {
        stringResource(R.string.library_day_header, day.year, day.month, day.day, bucket.total)
    }
    Text(
        text = label,
        style = MaterialTheme.typography.titleSmall,
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surface)
            .padding(Spacing.sm),
    )
}
