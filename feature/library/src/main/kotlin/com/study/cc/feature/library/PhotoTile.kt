package com.study.cc.feature.library

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import coil.ImageLoader
import coil.compose.AsyncImage
import com.study.cc.domain.model.PhotoMedia

@Composable
internal fun PhotoTile(media: PhotoMedia?, imageLoader: ImageLoader, modifier: Modifier = Modifier) {
    if (media == null) {
        Box(modifier = modifier.fillMaxSize().background(MaterialTheme.colorScheme.surfaceVariant))
    } else {
        AsyncImage(
            model = media.contentUri,
            imageLoader = imageLoader,
            contentDescription = stringResource(
                if (media.isVideo) R.string.library_video_thumbnail else R.string.library_photo_thumbnail,
            ),
            contentScale = ContentScale.Crop,
            modifier = modifier.fillMaxSize().background(MaterialTheme.colorScheme.surfaceVariant),
        )
    }
}
