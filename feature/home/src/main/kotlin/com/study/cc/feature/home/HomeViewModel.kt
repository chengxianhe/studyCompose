package com.study.cc.feature.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.study.cc.domain.model.ResearchSignal
import com.study.cc.domain.usecase.GetHomeSummaryUseCase
import com.study.cc.domain.usecase.GetQuoteUseCase
import com.study.cc.domain.usecase.GetResearchSignalsUseCase
import com.study.cc.domain.usecase.RefreshResearchSignalsUseCase
import com.study.cc.domain.usecase.ResolveSecurityIdUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
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
    private val getQuoteUseCase: GetQuoteUseCase,
    private val resolveSecurityIdUseCase: ResolveSecurityIdUseCase,
) : ViewModel() {
    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    private var observeJob: Job? = null
    private var quoteJob: Job? = null
    private var quoteLoadVersion = 0L
    private var lastQuotedSignals: List<ResearchSignal>? = null

    init {
        observeHomeData()
    }

    fun onRefreshClick() {
        if (_uiState.value.isRefreshing) return
        viewModelScope.launch {
            _uiState.update { it.copy(isRefreshing = true) }
            val previousQuoteLoadVersion = quoteLoadVersion
            try {
                runCatching { refreshResearchSignalsUseCase() }
                    .onSuccess {
                        if (quoteLoadVersion == previousQuoteLoadVersion) loadQuotes(_uiState.value.signals)
                    }
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
        quoteJob?.cancel()
        _uiState.update { it.copy(quotes = emptyMap()) }
        _uiState.update { it.copy(hasError = false, isLoading = true) }
        observeHomeData()
        onRefreshClick()
    }

    private fun observeHomeData() {
        observeJob?.cancel()
        lastQuotedSignals = null
        observeJob =
            combine(getHomeSummaryUseCase(), getResearchSignalsUseCase()) { summary, signals -> summary to signals }
                .onEach { (summary, signals) ->
                    _uiState.update { it.copy(summary = summary, signals = signals, isLoading = false) }
                    if (signals != lastQuotedSignals) {
                        lastQuotedSignals = signals
                        loadQuotes(signals)
                    }
                }
                .catch { throwable ->
                    if (throwable is CancellationException) throw throwable
                    _uiState.update { it.copy(isLoading = false, hasError = true) }
                }
                .launchIn(viewModelScope)
    }

    private fun loadQuotes(signals: List<ResearchSignal>) {
        quoteJob?.cancel()
        val version = ++quoteLoadVersion
        _uiState.update { it.copy(quotes = emptyMap()) }
        quoteJob =
            viewModelScope.launch {
                val quotes =
                    coroutineScope {
                        signals.map { signal ->
                            async {
                                val security = resolveSecurityIdUseCase(signal.stockCode) ?: return@async null
                                runCatching { getQuoteUseCase(security) }
                                    .onFailure { throwable ->
                                        if (throwable is CancellationException) throw throwable
                                    }.getOrNull()?.let { signal.id to it }
                            }
                        }.awaitAll().filterNotNull().toMap()
                    }
                if (version == quoteLoadVersion) _uiState.update { it.copy(quotes = quotes) }
            }
    }
}
