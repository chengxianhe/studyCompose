package com.study.cc.domain.model

/** 用户对媒体库的授权程度；`PARTIAL` 表示只授权了用户挑选的那部分（Android 14+）。 */
enum class PhotoAccess { NONE, PARTIAL, FULL }
