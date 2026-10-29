package com.study.cc.navigation

import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.navigation3.runtime.NavKey
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.ui.NavDisplay
import com.study.cc.R
import com.study.cc.feature.home.HomeRoute

/** App shell: bottom bar with the four tabs and the navigation display for the selected tab. */
@Composable
fun AppNavHost(modifier: Modifier = Modifier) {
    val state =
        rememberNavigationState(
            startRoute = PhotosRoute,
            topLevelRoutes = topLevelDestinations.map { it.route }.toSet(),
        )
    val navigator = remember(state) { Navigator(state) }
    val entryProvider =
        entryProvider<NavKey> {
            entry<PhotosRoute> { HomeRoute() }
            entry<AlbumsRoute> { TabPlaceholderScreen(R.string.tab_albums) }
            entry<MemoriesRoute> { TabPlaceholderScreen(R.string.tab_memories) }
            entry<EditorRoute> { TabPlaceholderScreen(R.string.tab_editor) }
        }
    Scaffold(
        modifier = modifier,
        // Each tab screen has its own Scaffold that handles the top inset; the bar handles the bottom one.
        contentWindowInsets = WindowInsets(0.dp),
        bottomBar = {
            NavigationBar {
                topLevelDestinations.forEach { destination ->
                    NavigationBarItem(
                        selected = destination.route == state.topLevelRoute,
                        onClick = { navigator.navigate(destination.route) },
                        icon = { Icon(painterResource(destination.icon), contentDescription = null) },
                        label = { Text(text = stringResource(destination.label)) },
                    )
                }
            }
        },
    ) { innerPadding ->
        NavDisplay(
            entries = state.toDecoratedEntries(entryProvider),
            onBack = navigator::goBack,
            modifier = Modifier.padding(innerPadding),
        )
    }
}
