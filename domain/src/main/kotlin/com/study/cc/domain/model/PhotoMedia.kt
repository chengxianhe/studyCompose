package com.study.cc.domain.model

/** MediaStore id and content URI are strings so the domain layer has no Android types. */
data class PhotoMedia(val id: String, val contentUri: String, val isVideo: Boolean)
