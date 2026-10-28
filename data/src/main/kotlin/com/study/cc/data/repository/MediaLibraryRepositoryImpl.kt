package com.study.cc.data.repository

import com.study.cc.core.logging.Logger
import com.study.cc.data.access.PhotoAccessProvider
import com.study.cc.data.di.MediaSyncScope
import com.study.cc.data.mediastore.MediaStoreChanges
import com.study.cc.data.sync.MediaLibrarySyncer
import com.study.cc.domain.model.LibrarySyncState
import com.study.cc.domain.model.PhotoAccess
import com.study.cc.domain.model.SyncStatus
import com.study.cc.domain.repository.MediaLibraryRepository
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.conflate
import kotlinx.coroutines.flow.merge
import kotlinx.coroutines.flow.onStart
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.concurrent.atomic.AtomicBoolean
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "MediaLibraryRepository"

@Singleton
internal class MediaLibraryRepositoryImpl @Inject constructor(
    private val syncer: MediaLibrarySyncer,
    private val accessProvider: PhotoAccessProvider,
    private val changes: MediaStoreChanges,
    @MediaSyncScope private val scope: CoroutineScope,
    private val logger: Logger,
) : MediaLibraryRepository {
    private val state =
        MutableStateFlow(LibrarySyncState(PhotoAccess.NONE, SyncStatus.Idle, itemCount = 0, lastSyncAtMs = null))
    private val triggers =
        MutableSharedFlow<Unit>(extraBufferCapacity = 1, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    private val started = AtomicBoolean(false)

    override fun observeSyncState(): Flow<LibrarySyncState> = state.asStateFlow().onStart { start() }

    override suspend fun refresh() {
        start()
        triggers.emit(Unit)
    }

    /** Starts once: merges manual refreshes and system media changes, syncs serially and coalesces a backlog. */
    private fun start() {
        if (!started.compareAndSet(false, true)) return
        scope.launch {
            merge(triggers, changes.changes()).onStart { emit(Unit) }.conflate().collect { runSync() }
        }
    }

    private suspend fun runSync() {
        val access = accessProvider.current()
        if (access == PhotoAccess.NONE) {
            state.update { it.copy(access = access, status = SyncStatus.Idle) }
            return
        }
        state.update { it.copy(access = access, status = SyncStatus.Syncing(processed = 0, total = null)) }
        runCatching {
            syncer.sync { processed, total ->
                state.update { it.copy(status = SyncStatus.Syncing(processed, total)) }
            }
        }.onSuccess { report ->
            val counts = report.counts
            logger.i(
                TAG,
                "sync ${report.mode} +${counts.inserted} ~${counts.updated} -${counts.deleted} ${report.durationMs}ms",
            )
            state.value = LibrarySyncState(access, SyncStatus.Idle, syncer.itemCount(), report.finishedAtMs)
        }.onFailure { error ->
            if (error is CancellationException) throw error
            logger.e(TAG, "sync failed", error)
            state.update { it.copy(status = SyncStatus.Failed) }
        }
    }
}
