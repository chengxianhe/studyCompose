package com.study.cc.navigation

import androidx.navigation3.runtime.NavKey

/** Applies navigation events to [NavigationState]. */
class Navigator(private val state: NavigationState) {
    /** A top level route switches tab; anything else is pushed onto the selected tab's stack. */
    fun navigate(route: NavKey) {
        if (route in state.backStacks.keys) {
            state.topLevelRoute = route
        } else {
            state.currentStack.add(route)
        }
    }

    /** Pops within the selected tab. At a tab's root nothing is popped, so the system can exit the app. */
    fun goBack() {
        val stack = state.currentStack
        if (stack.size > 1) stack.removeAt(stack.lastIndex)
    }
}
