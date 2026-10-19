package com.study.cc.domain.usecase

import com.study.cc.domain.model.DailySummary
import com.study.cc.domain.repository.ResearchSignalRepository
import kotlinx.coroutines.flow.Flow

class GetHomeSummaryUseCase(private val researchSignalRepository: ResearchSignalRepository) {
    operator fun invoke(): Flow<DailySummary> = researchSignalRepository.observeDailySummary()
}
