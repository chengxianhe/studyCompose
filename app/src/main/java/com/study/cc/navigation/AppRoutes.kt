package com.study.cc.navigation

import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
import androidx.navigation3.runtime.NavKey
import com.study.cc.R
import kotlinx.serialization.Serializable

/** Top level destinations. Each one owns a back stack and a bottom bar item. */
@Serializable
data object PhotosRoute : NavKey

@Serializable
data object AlbumsRoute : NavKey

@Serializable
data object MemoriesRoute : NavKey

@Serializable
data object EditorRoute : NavKey

data class TopLevelDestination(val route: NavKey, @StringRes val label: Int, @DrawableRes val icon: Int)

val topLevelDestinations: List<TopLevelDestination> =
    listOf(
        TopLevelDestination(PhotosRoute, R.string.tab_photos, R.drawable.ic_tab_photos),
        TopLevelDestination(AlbumsRoute, R.string.tab_albums, R.drawable.ic_tab_albums),
        TopLevelDestination(MemoriesRoute, R.string.tab_memories, R.drawable.ic_tab_memories),
        TopLevelDestination(EditorRoute, R.string.tab_editor, R.drawable.ic_tab_editor),
    )
