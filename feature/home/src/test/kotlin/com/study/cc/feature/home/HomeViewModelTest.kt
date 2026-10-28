package com.study.cc.feature.home

import app.cash.turbine.test
import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.LibrarySyncState
import com.study.cc.domain.model.PhotoAccess
import com.study.cc.domain.model.SyncStatus
import com.study.cc.domain.repository.MediaLibraryRepository
import com.study.cc.domain.usecase.ObserveLibrarySyncStateUseCase
import com.study.cc.domain.usecase.RefreshMediaLibraryUseCase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Before
import org.junit.Test

private const val ITEM_COUNT = 42

private class FakeMediaLibraryRepository : MediaLibraryRepository {
    val state =
        MutableStateFlow(LibrarySyncState(PhotoAccess.NONE, SyncStatus.Idle, itemCount = 0, lastSyncAtMs = null))
    var refreshCount = 0

    override fun observeSyncState(): Flow<LibrarySyncState> = state

    override suspend fun refresh() {
        refreshCount++
    }
}

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModelTest {
    private val repository = FakeMediaLibraryRepository()

    @Before
    fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())

    @After
    fun tearDown() = Dispatchers.resetMain()

    private fun viewModel() =
        HomeViewModel(ObserveLibrarySyncStateUseCase(repository), RefreshMediaLibraryUseCase(repository))

    @Test
    fun exposesTheRepositoryStateAsUiState() = runTest {
        val viewModel = viewModel()

        viewModel.uiState.test {
            assertThat(awaitItem().library.access).isEqualTo(PhotoAccess.NONE)
            repository.state.value = LibrarySyncState(PhotoAccess.PARTIAL, SyncStatus.Idle, ITEM_COUNT, null)
            val updated = awaitItem().library
            assertThat(updated.access).isEqualTo(PhotoAccess.PARTIAL)
            assertThat(updated.itemCount).isEqualTo(ITEM_COUNT)
        }
    }

    @Test
    fun accessChangeTriggersARefresh() = runTest {
        viewModel().onAccessMayHaveChanged()

        assertThat(repository.refreshCount).isEqualTo(1)
    }
}
