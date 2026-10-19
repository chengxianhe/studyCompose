package com.study.cc.domain.model

data class ResearchSignal(
    val id: String,
    val stockCode: String,
    val stockName: String,
    val eventTitle: String,
    val eventScore: Int,
    val businessRelevancePercent: Int,
    val recentPriceChangePercent: Double,
    val sectorPriceChangePercent: Double,
    val historicalSimilarEventCount: Int,
    val historicalPositiveReturnRatioPercent: Double,
)
