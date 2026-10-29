package com.study.cc.navigation

import androidx.compose.runtime.mutableStateOf
import androidx.navigation3.runtime.NavBackStack
import androidx.navigation3.runtime.NavKey
import com.google.common.truth.Truth.assertThat
import kotlinx.serialization.Serializable
import org.junit.Test

@Serializable
private data object PhotoDetail : NavKey

@Serializable
private data object AlbumDetail : NavKey

class NavigatorTest {
    private val state =
        NavigationState(
            startRoute = PhotosRoute,
            topLevelRoute = mutableStateOf(PhotosRoute),
            backStacks = topLevelDestinations.associate { it.route to NavBackStack(it.route) },
        )
    private val navigator = Navigator(state)

    @Test
    fun navigatingToATopLevelRouteSwitchesTab() {
        navigator.navigate(AlbumsRoute)

        assertThat(state.topLevelRoute).isEqualTo(AlbumsRoute)
    }

    @Test
    fun otherRoutesArePushedOntoTheSelectedTabOnly() {
        navigator.navigate(PhotoDetail)

        assertThat(state.backStacks.getValue(PhotosRoute).toList()).containsExactly(PhotosRoute, PhotoDetail).inOrder()
        assertThat(state.backStacks.getValue(AlbumsRoute).toList()).containsExactly(AlbumsRoute)
    }

    @Test
    fun eachTabKeepsItsOwnStackWhenSwitching() {
        navigator.navigate(PhotoDetail)
        navigator.navigate(AlbumsRoute)
        navigator.navigate(AlbumDetail)
        navigator.navigate(PhotosRoute)

        assertThat(state.currentStack.toList()).containsExactly(PhotosRoute, PhotoDetail).inOrder()
        navigator.navigate(AlbumsRoute)
        assertThat(state.currentStack.toList()).containsExactly(AlbumsRoute, AlbumDetail).inOrder()
    }

    @Test
    fun goBackPopsWithinTheSelectedTab() {
        navigator.navigate(PhotoDetail)

        navigator.goBack()

        assertThat(state.currentStack.toList()).containsExactly(PhotosRoute)
        assertThat(state.topLevelRoute).isEqualTo(PhotosRoute)
    }

    @Test
    fun goBackAtATabRootLeavesTheStackAloneSoTheSystemCanExit() {
        navigator.navigate(AlbumsRoute)

        navigator.goBack()

        assertThat(state.topLevelRoute).isEqualTo(AlbumsRoute)
        assertThat(state.currentStack.toList()).containsExactly(AlbumsRoute)
    }

    @Test
    fun selectingTheCurrentTabAgainChangesNothing() {
        navigator.navigate(PhotoDetail)

        navigator.navigate(PhotosRoute)

        assertThat(state.currentStack.toList()).containsExactly(PhotosRoute, PhotoDetail).inOrder()
    }
}
