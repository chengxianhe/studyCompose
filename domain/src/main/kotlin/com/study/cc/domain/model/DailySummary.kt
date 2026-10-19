package com.study.cc.domain.model

data class DailySummary(
    val scannedNewsCount: Int,
    val mergedEventCount: Int,
    val effectiveEventCount: Int,
    val coreCandidateCount: Int,
)
