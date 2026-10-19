package com.study.cc.domain.usecase

import com.study.cc.domain.model.ResearchSignal
import com.study.cc.domain.repository.ResearchSignalRepository
import kotlinx.coroutines.flow.Flow

class GetResearchSignalsUseCase(
    private val researchSignalRepository: ResearchSignalRepository,
) {
    operator fun invoke(): Flow<List<ResearchSignal>> = researchSignalRepository.observeSignals()
}
