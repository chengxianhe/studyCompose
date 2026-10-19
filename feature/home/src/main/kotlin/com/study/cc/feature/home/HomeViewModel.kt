package com.study.cc.feature.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.study.cc.domain.usecase.GetHomeSummaryUseCase
import com.study.cc.domain.usecase.GetResearchSignalsUseCase
import com.study.cc.domain.usecase.RefreshResearchSignalsUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HomeViewModel
@Inject
constructor(
    private val getHomeSummaryUseCase: GetHomeSummaryUseCase,
    private val getResearchSignalsUseCase: GetResearchSignalsUseCase,
    private val refreshResearchSignalsUseCase: RefreshResearchSignalsUseCase,
) : ViewModel() {
    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    private var observeJob: Job? = null

    init {
        observeHomeData()
    }

    fun onRefreshClick() {
        if (_uiState.value.isRefreshing) return
        viewModelScope.launch {
            _uiState.update { it.copy(isRefreshing = true) }
            try {
                runCatching { refreshResearchSignalsUseCase() }
                    .onFailure { throwable ->
                        if (throwable is CancellationException) throw throwable
                        _uiState.update { it.copy(hasError = true) }
                    }
            } finally {
                _uiState.update { it.copy(isRefreshing = false) }
            }
        }
    }

    fun onRetryClick() {
        _uiState.update { it.copy(hasError = false, isLoading = true) }
        observeHomeData()
        onRefreshClick()
    }

    private fun observeHomeData() {
        observeJob?.cancel()
        observeJob =
            combine(getHomeSummaryUseCase(), getResearchSignalsUseCase()) { summary, signals -> summary to signals }
                .onEach { (summary, signals) ->
                    _uiState.update { it.copy(summary = summary, signals = signals, isLoading = false) }
                }
                .catch {
                    _uiState.update { it.copy(isLoading = false, hasError = true) }
                }
                .launchIn(viewModelScope)
    }
}
