package com.study.cc.feature.library

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.PhotoDayBucket
import com.study.cc.domain.usecase.GetPhotoDayItemsUseCase
import com.study.cc.domain.usecase.ObserveLibrarySyncStateUseCase
import com.study.cc.domain.usecase.ObservePhotoDayBucketsUseCase
import com.study.cc.domain.usecase.RefreshMediaLibraryUseCase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class PhotoDayBucketRetryTest {
    @Test
    fun retryResubscribesAfterBucketObservationFails() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            var subscriptions = 0
            val repository = ControlledTimeline().apply {
                observe = {
                    flow {
                        subscriptions++
                        if (subscriptions == 1) error("temporary bucket failure")
                        emit(listOf(PhotoDayBucket(firstDay, 1)))
                    }
                }
            }
            val viewModel = PhotoDayViewModel(
                ObserveLibrarySyncStateUseCase(IdleLibrary),
                ObservePhotoDayBucketsUseCase(repository),
                GetPhotoDayItemsUseCase(repository),
                RefreshMediaLibraryUseCase(IdleLibrary),
                SilentLogger,
            )
            runCurrent()
            assertThat(viewModel.uiState.value.bucketLoadFailed).isTrue()

            viewModel.retry()
            runCurrent()

            assertThat(subscriptions).isEqualTo(2)
            assertThat(viewModel.uiState.value.loadFailed).isFalse()
            assertThat(viewModel.uiState.value.buckets).containsExactly(PhotoDayBucket(firstDay, 1))
        } finally {
            Dispatchers.resetMain()
        }
    }
}
