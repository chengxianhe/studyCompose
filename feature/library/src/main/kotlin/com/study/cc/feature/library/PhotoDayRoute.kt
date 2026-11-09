package com.study.cc.feature.library

import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.study.cc.core.common.MediaPermissions

@Composable
fun PhotoDayRoute(modifier: Modifier = Modifier, viewModel: PhotoDayViewModel = hiltViewModel()) {
    val context = LocalContext.current
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val imageLoader = remember(context.applicationContext) { PhotoImageLoader.get(context) }
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        viewModel.onAccessMayHaveChanged()
    }
    LifecycleResumeEffect(Unit) {
        viewModel.onAccessMayHaveChanged()
        onPauseOrDispose {}
    }
    PhotoDayScreen(
        uiState = uiState,
        imageLoader = imageLoader,
        actions = PhotoDayActions(
            onGrantClick = { permissionLauncher.launch(MediaPermissions.requestedFor(Build.VERSION.SDK_INT)) },
            onRetryClick = viewModel::retry,
            onDaysVisible = viewModel::onVisibleDaysChanged,
        ),
        modifier = modifier,
    )
}
