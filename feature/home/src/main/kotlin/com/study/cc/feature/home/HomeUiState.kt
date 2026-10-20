package com.study.cc.feature.home

import com.study.cc.domain.model.DailySummary
import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.ResearchSignal

data class HomeUiState(
    val summary: DailySummary? = null,
    val signals: List<ResearchSignal> = emptyList(),
    val quotes: Map<String, Quote> = emptyMap(),
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val hasError: Boolean = false,
)
