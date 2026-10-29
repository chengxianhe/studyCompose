package com.study.cc.navigation

import androidx.annotation.StringRes
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.study.cc.R
import com.study.cc.core.ui.state.EmptyState

/** Stand-in for tabs whose real screens arrive in later tasks. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TabPlaceholderScreen(@StringRes titleRes: Int, modifier: Modifier = Modifier) {
    Scaffold(
        modifier = modifier,
        topBar = { TopAppBar(title = { Text(text = stringResource(titleRes)) }) },
    ) { innerPadding ->
        EmptyState(
            message = stringResource(R.string.tab_placeholder_message),
            modifier = Modifier.padding(innerPadding),
        )
    }
}
