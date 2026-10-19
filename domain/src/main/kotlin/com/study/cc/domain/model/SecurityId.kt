package com.study.cc.domain.model

private const val CODE_LENGTH = 6

data class SecurityId(val market: Market, val code: String) {
    init {
        require(code.length == CODE_LENGTH && code.all { it in '0'..'9' })
    }
}
