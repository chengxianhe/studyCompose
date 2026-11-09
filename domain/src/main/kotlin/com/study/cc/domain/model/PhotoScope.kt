package com.study.cc.domain.model

/** A timeline's data range. Album and memory ranges can be added without changing the day-stream contract. */
sealed interface PhotoScope {
    data object All : PhotoScope
}
