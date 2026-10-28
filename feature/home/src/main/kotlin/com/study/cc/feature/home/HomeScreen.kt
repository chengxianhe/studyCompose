package com.study.cc.feature.home

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import com.study.cc.core.designsystem.theme.AppTheme
import com.study.cc.core.ui.state.EmptyState

@Composable
fun HomeRoute(modifier: Modifier = Modifier) {
    HomeScreen(modifier = modifier)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(modifier: Modifier = Modifier) {
    Scaffold(
        modifier = modifier,
        topBar = { TopAppBar(title = { Text(text = stringResource(R.string.home_title)) }) },
    ) { innerPadding ->
        EmptyState(
            message = stringResource(R.string.home_empty_message),
            modifier = Modifier.padding(innerPadding),
        )
    }
}

@Preview(showBackground = true)
@Composable
internal fun HomeScreenPreview() {
    AppTheme {
        HomeScreen()
    }
}
