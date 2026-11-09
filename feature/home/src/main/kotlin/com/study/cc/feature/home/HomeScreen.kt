package com.study.cc.feature.home

import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.study.cc.core.common.MediaPermissions

@Composable
fun HomeRoute(modifier: Modifier = Modifier, viewModel: HomeViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    // The result is picked up by the resume effect below, which runs after the permission dialog closes.
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {}
    LifecycleResumeEffect(Unit) {
        viewModel.onAccessMayHaveChanged()
        onPauseOrDispose {}
    }
    HomeScreen(
        uiState = uiState,
        onGrantClick = { permissionLauncher.launch(MediaPermissions.requestedFor(Build.VERSION.SDK_INT)) },
        onRetryClick = viewModel::onAccessMayHaveChanged,
        modifier = modifier,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    uiState: HomeUiState,
    onGrantClick: () -> Unit,
    onRetryClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Scaffold(
        modifier = modifier,
        topBar = { TopAppBar(title = { Text(text = stringResource(R.string.home_title)) }) },
    ) { innerPadding ->
        LibraryAccessPanel(
            library = uiState.library,
            onGrantClick = onGrantClick,
            onRetryClick = onRetryClick,
            modifier = Modifier.padding(innerPadding),
        )
    }
}
