package com.study.cc.feature.library

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.PhotoMedia
import com.study.cc.domain.usecase.GetPhotoDayItemsUseCase
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.withContext
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class PhotoDayLoadsTest {
    @Test
    fun leavingViewportCancelsQueryAndClearsLoading() = runTest {
        var cancelled = false
        val repository = ControlledTimeline().apply {
            query = {
                try {
                    awaitCancellation()
                } finally {
                    cancelled = true
                }
            }
        }
        val loads = PhotoDayLoads(backgroundScope, GetPhotoDayItemsUseCase(repository), SilentLogger)
        loads.updateBuckets(setOf(firstDay))
        loads.updateVisible(setOf(firstDay))
        runCurrent()
        assertThat(loads.state.value.loading).containsExactly(firstDay)

        loads.updateVisible(emptySet())
        runCurrent()

        assertThat(cancelled).isTrue()
        assertThat(loads.state.value.loading).isEmpty()
        assertThat(loads.state.value.failed).isFalse()
    }

    @Test
    fun lateCancelledResultCannotOverwriteReenteredDay() = runTest {
        val oldResult = CompletableDeferred<List<PhotoMedia>>()
        val freshItems = listOf(PhotoMedia("new", "content://photo/new", false))
        var calls = 0
        val repository = ControlledTimeline().apply {
            query = {
                calls++
                if (calls == 1) withContext(NonCancellable) { oldResult.await() } else freshItems
            }
        }
        val loads = PhotoDayLoads(backgroundScope, GetPhotoDayItemsUseCase(repository), SilentLogger)
        loads.updateBuckets(setOf(firstDay))
        loads.updateVisible(setOf(firstDay))
        runCurrent()
        loads.updateVisible(emptySet())
        loads.updateVisible(setOf(firstDay))
        runCurrent()

        oldResult.complete(listOf(PhotoMedia("old", "content://photo/old", false)))
        runCurrent()

        assertThat(calls).isEqualTo(2)
        assertThat(loads.state.value.items[firstDay]).isEqualTo(freshItems)
        assertThat(loads.state.value.loading).isEmpty()
    }

    @Test
    fun retryRestartsFailedVisibleQuery() = runTest {
        var calls = 0
        val repository = ControlledTimeline().apply {
            query = {
                calls++
                if (calls == 1) error("temporary query failure")
                emptyList()
            }
        }
        val loads = PhotoDayLoads(backgroundScope, GetPhotoDayItemsUseCase(repository), SilentLogger)
        loads.updateBuckets(setOf(firstDay))
        loads.updateVisible(setOf(firstDay))
        runCurrent()
        assertThat(loads.state.value.failed).isTrue()

        loads.retry()
        runCurrent()

        assertThat(calls).isEqualTo(2)
        assertThat(loads.state.value.failed).isFalse()
        assertThat(loads.state.value.items).containsKey(firstDay)
    }
}
