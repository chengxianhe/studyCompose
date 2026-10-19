package com.study.cc.domain.repository

import com.study.cc.domain.model.DailySummary
import com.study.cc.domain.model.ResearchSignal
import kotlinx.coroutines.flow.Flow

interface ResearchSignalRepository {
    fun observeDailySummary(): Flow<DailySummary>

    fun observeSignals(): Flow<List<ResearchSignal>>

    suspend fun refresh()
}
