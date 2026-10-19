package com.study.cc.domain.usecase

import com.study.cc.domain.repository.ResearchSignalRepository

class RefreshResearchSignalsUseCase(
    private val researchSignalRepository: ResearchSignalRepository,
) {
    suspend operator fun invoke() {
        researchSignalRepository.refresh()
    }
}
