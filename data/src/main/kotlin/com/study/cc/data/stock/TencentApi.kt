package com.study.cc.data.stock

import okhttp3.ResponseBody
import retrofit2.http.GET
import retrofit2.http.Url

internal interface TencentApi {
    @GET
    suspend fun get(@Url url: String): ResponseBody
}
