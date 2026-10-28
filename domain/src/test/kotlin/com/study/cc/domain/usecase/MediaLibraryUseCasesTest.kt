package com.study.cc.domain.usecase

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.LibrarySyncState
import com.study.cc.domain.model.PhotoAccess
import com.study.cc.domain.model.SyncStatus
import com.study.cc.domain.repository.MediaLibraryRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import org.junit.Test

private class FakeMediaLibraryRepository(private val states: List<LibrarySyncState>) : MediaLibraryRepository {
    var refreshCount = 0

    override fun observeSyncState(): Flow<LibrarySyncState> = flowOf(*states.toTypedArray())

    override suspend fun refresh() {
        refreshCount++
    }
}

class MediaLibraryUseCasesTest {
    private val state = LibrarySyncState(PhotoAccess.PARTIAL, SyncStatus.Idle, itemCount = 3, lastSyncAtMs = null)

    @Test
    fun observeForwardsRepositoryStates() = runTest {
        val repository = FakeMediaLibraryRepository(listOf(state))

        assertThat(ObserveLibrarySyncStateUseCase(repository)().toList()).containsExactly(state)
    }

    @Test
    fun refreshDelegatesToRepository() = runTest {
        val repository = FakeMediaLibraryRepository(emptyList())

        RefreshMediaLibraryUseCase(repository)()

        assertThat(repository.refreshCount).isEqualTo(1)
    }
}
