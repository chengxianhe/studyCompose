package com.study.cc.feature.library

import com.study.cc.domain.model.PhotoDay

data class PhotoDayActions(
    val onGrantClick: () -> Unit,
    val onRetryClick: () -> Unit,
    val onDaysVisible: (Set<PhotoDay>) -> Unit,
)

