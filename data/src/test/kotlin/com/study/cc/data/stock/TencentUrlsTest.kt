package com.study.cc.data.stock

import com.google.common.truth.Truth.assertThat
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import org.junit.Test

class TencentUrlsTest {
    @Test
    fun exactUrls() {
        val security = SecurityId(Market.SSE, "600519")
        assertThat(TencentUrls.quote(security)).isEqualTo("https://qt.gtimg.cn/q=sh600519")
        assertThat(TencentUrls.daily(security, DEFAULT_LIMIT))
            .isEqualTo("https://web.ifzq.gtimg.cn/appstock/app/newfqkline/get?param=sh600519,day,,,250,qfq")
        assertThat(TencentUrls.search("贵州 茅台"))
            .isEqualTo("https://smartbox.gtimg.cn/s3/?q=%E8%B4%B5%E5%B7%9E%20%E8%8C%85%E5%8F%B0&t=all")
        assertThat(TencentUrls.quote(SecurityId(Market.SZSE, "000001")))
            .isEqualTo("https://qt.gtimg.cn/q=sz000001")
    }

    private companion object {
        const val DEFAULT_LIMIT = 250
    }
}
