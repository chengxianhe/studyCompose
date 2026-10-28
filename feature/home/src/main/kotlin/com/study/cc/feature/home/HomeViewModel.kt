package com.study.cc.feature.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.study.cc.domain.usecase.ObserveLibrarySyncStateUseCase
import com.study.cc.domain.usecase.RefreshMediaLibraryUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HomeViewModel @Inject constructor(
    observeLibrarySyncState: ObserveLibrarySyncStateUseCase,
    private val refreshMediaLibrary: RefreshMediaLibraryUseCase,
) : ViewModel() {
    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        observeLibrarySyncState().onEach { library ->
            _uiState.value = HomeUiState(library = library)
        }.launchIn(viewModelScope)
    }

    /** The user answered the permission dialog or came back from settings: re-evaluate access and sync. */
    fun onAccessMayHaveChanged() {
        viewModelScope.launch { refreshMediaLibrary() }
    }
}
