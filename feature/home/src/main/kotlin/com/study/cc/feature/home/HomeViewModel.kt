package com.study.cc.feature.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.study.cc.core.logging.Logger
import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.ResearchSignal
import com.study.cc.domain.model.StockDataException
import com.study.cc.domain.usecase.GetHomeSummaryUseCase
import com.study.cc.domain.usecase.GetResearchSignalsUseCase
import com.study.cc.domain.usecase.GetSignalQuoteUseCase
import com.study.cc.domain.usecase.RefreshResearchSignalsUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
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

private const val TAG = "HomeViewModel"

@HiltViewModel
class HomeViewModel
@Inject
constructor(
    private val getHomeSummaryUseCase: GetHomeSummaryUseCase,
    private val getResearchSignalsUseCase: GetResearchSignalsUseCase,
    private val refreshResearchSignalsUseCase: RefreshResearchSignalsUseCase,
    private val getSignalQuoteUseCase: GetSignalQuoteUseCase,
    private val logger: Logger,
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

    fun onRefreshClick() = refresh(reloadQuotes = true)

    private fun refresh(reloadQuotes: Boolean) {
        if (_uiState.value.isRefreshing) return
        viewModelScope.launch {
            _uiState.update { it.copy(isRefreshing = true) }
            val previousQuoteLoadVersion = quoteLoadVersion
            try {
                runCatching { refreshResearchSignalsUseCase() }
                    .onSuccess {
                        if (reloadQuotes &&
                            quoteLoadVersion == previousQuoteLoadVersion
                        ) {
                            loadQuotes(_uiState.value.signals)
                        }
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
        refresh(reloadQuotes = false)
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
        val ids = signals.map(ResearchSignal::id).toSet()
        _uiState.update { state -> state.copy(quotes = state.quotes.filterKeys { it in ids }) }
        quoteJob =
            viewModelScope.launch {
                coroutineScope {
                    signals.forEach { signal -> launch { loadQuote(signal, version) } }
                }
            }
    }

    private suspend fun loadQuote(signal: ResearchSignal, version: Long) {
        val quote =
            runCatching { getSignalQuoteUseCase(signal) }
                .onFailure { throwable ->
                    if (throwable is CancellationException) throw throwable
                    if (throwable !is StockDataException) logger.w(TAG, "Quote load failed", throwable)
                }.getOrNull()
        _uiState.update { state -> if (version == quoteLoadVersion) state.withQuote(signal.id, quote) else state }
    }
}

private fun HomeUiState.withQuote(id: String, quote: Quote?): HomeUiState =
    copy(quotes = if (quote == null) quotes - id else quotes + (id to quote))
