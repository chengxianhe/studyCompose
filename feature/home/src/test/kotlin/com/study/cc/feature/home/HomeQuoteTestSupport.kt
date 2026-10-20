package com.study.cc.feature.home

import com.study.cc.core.logging.Logger
import com.study.cc.domain.model.DailySummary
import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.ResearchSignal
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.repository.ResearchSignalRepository
import com.study.cc.domain.usecase.GetHomeSummaryUseCase
import com.study.cc.domain.usecase.GetQuoteUseCase
import com.study.cc.domain.usecase.GetResearchSignalsUseCase
import com.study.cc.domain.usecase.GetSignalQuoteUseCase
import com.study.cc.domain.usecase.RefreshResearchSignalsUseCase
import com.study.cc.domain.usecase.ResolveSecurityIdUseCase
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import java.time.Instant

private const val EVENT_SCORE = 80
private const val BUSINESS_RELEVANCE = 90
private const val SIMILAR_EVENT_COUNT = 3
private const val POSITIVE_RETURN_RATIO = 60.0

internal class SignalRepository(initial: List<ResearchSignal>) : ResearchSignalRepository {
    val signals = MutableStateFlow(initial)
    val summary = MutableStateFlow(DailySummary(0, 0, 0, 0))

    override fun observeDailySummary(): Flow<DailySummary> = summary

    override fun observeSignals(): Flow<List<ResearchSignal>> = signals

    override suspend fun refresh() = Unit
}

internal fun homeViewModel(
    repository: ResearchSignalRepository,
    logger: Logger = NoOpLogger,
    onQuote: suspend (SecurityId) -> Quote,
): HomeViewModel = HomeViewModel(
    getHomeSummaryUseCase = GetHomeSummaryUseCase(repository),
    getResearchSignalsUseCase = GetResearchSignalsUseCase(repository),
    refreshResearchSignalsUseCase = RefreshResearchSignalsUseCase(repository),
    getSignalQuoteUseCase = GetSignalQuoteUseCase(
        ResolveSecurityIdUseCase(),
        GetQuoteUseCase(FakeQuoteRepository(onQuote)),
    ),
    logger = logger,
)

internal fun testSignal(id: String, code: String): ResearchSignal = ResearchSignal(
    id,
    code,
    "name",
    "event",
    EVENT_SCORE,
    BUSINESS_RELEVANCE,
    1.0,
    2.0,
    SIMILAR_EVENT_COUNT,
    POSITIVE_RETURN_RATIO,
)

internal fun testQuote(security: SecurityId, price: Double = 1.0): Quote =
    Quote(security, "name", price, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 1, 1.0, 0.0, "test", Instant.EPOCH, Instant.EPOCH)
