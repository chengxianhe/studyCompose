package com.study.cc.domain.usecase

import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.ResearchSignal

class GetSignalQuoteUseCase(
    private val resolveSecurityIdUseCase: ResolveSecurityIdUseCase,
    private val getQuoteUseCase: GetQuoteUseCase,
) {
    suspend operator fun invoke(signal: ResearchSignal): Quote? {
        val security = resolveSecurityIdUseCase(signal.stockCode) ?: return null
        return getQuoteUseCase(security)
    }
}
