package com.study.cc.feature.library

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.study.cc.core.logging.Logger
import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoScope
import com.study.cc.domain.usecase.GetPhotoDayItemsUseCase
import com.study.cc.domain.usecase.ObserveLibrarySyncStateUseCase
import com.study.cc.domain.usecase.ObservePhotoDayBucketsUseCase
import com.study.cc.domain.usecase.RefreshMediaLibraryUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

private const val TAG = "PhotoDayViewModel"

@OptIn(ExperimentalCoroutinesApi::class)
@HiltViewModel
class PhotoDayViewModel @Inject constructor(
    observeLibrarySyncState: ObserveLibrarySyncStateUseCase,
    observePhotoDayBuckets: ObservePhotoDayBucketsUseCase,
    getPhotoDayItems: GetPhotoDayItemsUseCase,
    private val refreshMediaLibrary: RefreshMediaLibraryUseCase,
    private val logger: Logger,
) : ViewModel() {
    private val _uiState = MutableStateFlow(PhotoDayUiState())
    val uiState: StateFlow<PhotoDayUiState> = _uiState.asStateFlow()
    private val loads = PhotoDayLoads(viewModelScope, getPhotoDayItems, logger)
    private val bucketAttempts = MutableStateFlow(0)

    init {
        observeLibrarySyncState().onEach { library ->
            _uiState.update { it.copy(library = library) }
        }.launchIn(viewModelScope)
        loads.state.onEach { loads ->
            _uiState.update {
                it.copy(itemsByDay = loads.items, loadingDays = loads.loading, itemLoadFailed = loads.failed)
            }
        }.launchIn(viewModelScope)
        bucketAttempts.flatMapLatest {
            observePhotoDayBuckets(PhotoScope.All).onEach { buckets ->
                _uiState.update { it.copy(buckets = buckets, bucketsLoaded = true, bucketLoadFailed = false) }
                loads.updateBuckets(buckets.map { it.day }.toSet())
            }.catch { error ->
                if (error is CancellationException) throw error
                logger.e(TAG, "day bucket query failed", error)
                _uiState.update { it.copy(bucketLoadFailed = true, bucketsLoaded = true) }
            }
        }.launchIn(viewModelScope)
    }

    fun onAccessMayHaveChanged() {
        viewModelScope.launch { refreshMediaLibrary() }
    }

    fun onVisibleDaysChanged(days: Set<PhotoDay>) {
        loads.updateVisible(days)
    }

    fun retry() {
        if (_uiState.value.bucketLoadFailed) {
            _uiState.update { it.copy(bucketLoadFailed = false, bucketsLoaded = false) }
            bucketAttempts.update { it + 1 }
        }
        loads.retry()
        onAccessMayHaveChanged()
    }
}
