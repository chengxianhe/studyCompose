package com.study.cc.data.repository

import com.google.common.truth.Truth.assertThat
import com.study.cc.core.logging.Logger
import com.study.cc.data.stock.TencentApi
import com.study.cc.domain.model.Market
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.StockDataException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response
import java.io.IOException
import java.time.Clock
import java.time.Instant
import java.time.ZoneOffset

class StockMarketRepositoryImplTest {
    private val security = SecurityId(Market.SSE, "600519")
    private val instant = Instant.parse("2026-10-19T08:30:00Z")
    private val clock = Clock.fixed(instant, ZoneOffset.UTC)

    @Test
    fun `三种响应映射正确且 URL 符合腾讯协议`() = runTest {
        val api = FakeApi()
        val repository = StockMarketRepositoryImpl(api, clock, FakeLogger())
        api.body = bytes("quote_sh600519.gbk")
        val quote = repository.getQuote(security)
        assertThat(quote.name).isEqualTo("贵州茅台")
        assertThat(quote.fetchedAt).isEqualTo(instant)
        assertThat(api.lastUrl).isEqualTo("https://qt.gtimg.cn/q=sh600519")

        api.body = bytes("kline_sh600519_day5.json")
        val bars = repository.getDailyBars(security, BAR_LIMIT)
        assertThat(bars.bars).hasSize(BAR_LIMIT)
        assertThat(bars.fetchedAt).isEqualTo(instant)
        assertThat(api.lastUrl).isEqualTo(DAILY_URL)

        api.body = bytes("search_600519.txt")
        assertThat(repository.searchSecurities("600519").single().name).isEqualTo("贵州茅台")
        assertThat(api.lastUrl).isEqualTo("https://smartbox.gtimg.cn/s3/?q=600519&t=all")
    }

    @Test
    fun `IO 与 HTTP 403 429 500 均映射为上游不可用并保留原因`() = runTest {
        val api = FakeApi()
        val repository = StockMarketRepositoryImpl(api, clock, FakeLogger())
        val io = IOException("private response text")
        api.error = io
        val ioFailure = failure(StockDataException.UpstreamUnavailable::class.java) {
            repository.getQuote(security)
        }
        assertThat(ioFailure.cause).isSameInstanceAs(io)
        listOf(FORBIDDEN, TOO_MANY_REQUESTS, SERVER_ERROR).forEach { status ->
            val http = HttpException(
                Response.error<Any>(status, "failure".toResponseBody("text/plain".toMediaType())),
            )
            api.error = http
            val httpFailure = failure(StockDataException.UpstreamUnavailable::class.java) {
                repository.getQuote(security)
            }
            assertThat(httpFailure.cause).isSameInstanceAs(http)
        }
    }

    @Test
    fun `取消异常原样传播`() = runTest {
        val api = FakeApi()
        val cancellation = CancellationException("cancel")
        api.error = cancellation
        val caught = failure(CancellationException::class.java) {
            StockMarketRepositoryImpl(api, clock, FakeLogger()).getQuote(security)
        }
        assertThat(caught).isSameInstanceAs(cancellation)
    }

    @Test
    fun `失败日志不包含响应正文`() = runTest {
        val api = FakeApi()
        val logger = FakeLogger()
        api.body = "response secret sentinel".toByteArray().toResponseBody()
        failure(StockDataException.SchemaChanged::class.java) {
            StockMarketRepositoryImpl(api, clock, logger).getQuote(security)
        }
        assertThat(logger.messages).hasSize(1)
        assertThat(logger.messages.single()).contains("600519")
        assertThat(logger.messages.single()).doesNotContain("response secret sentinel")
    }

    @Test
    fun `三种成功调用各写一条信息日志且不泄露查询或响应`() = runTest {
        val api = FakeApi()
        val logger = FakeLogger()
        val repository = StockMarketRepositoryImpl(api, clock, logger)

        api.body = bytes("quote_sh600519.gbk")
        repository.getQuote(security)
        assertThat(logger.infoMessages).containsExactly("StockMarketRepositoryImpl getQuote ok 600519")
        assertThat(logger.infoMessages.single()).doesNotContain("贵州茅台")

        logger.infoMessages.clear()
        api.body = bytes("kline_sh600519_day5.json")
        repository.getDailyBars(security, BAR_LIMIT)
        assertThat(logger.infoMessages).containsExactly("StockMarketRepositoryImpl getDailyBars ok 600519 count=5")
        assertThat(logger.infoMessages.single()).doesNotContain("qfqday")

        logger.infoMessages.clear()
        api.body = bytes("search_600519.txt")
        repository.searchSecurities("private search text")
        assertThat(logger.infoMessages).containsExactly("StockMarketRepositoryImpl searchSecurities ok count=1")
        assertThat(logger.infoMessages.single()).doesNotContain("private search text")
        assertThat(logger.infoMessages.single()).doesNotContain("\\u8d35")
    }

    private suspend fun <T : Throwable> failure(type: Class<T>, operation: suspend () -> Any?): T {
        try {
            operation()
        } catch (error: Throwable) {
            assertThat(error).isInstanceOf(type)
            return type.cast(error)
        }
        throw AssertionError("Expected ${type.simpleName}")
    }

    private fun bytes(name: String): ResponseBody {
        val resource = requireNotNull(javaClass.getResourceAsStream("/stock/tencent/$name"))
        return resource.use { it.readBytes().toResponseBody() }
    }

    private class FakeApi : TencentApi {
        lateinit var body: ResponseBody
        var error: Throwable? = null
        var lastUrl: String? = null

        override suspend fun get(url: String): ResponseBody {
            lastUrl = url
            error?.let { throw it }
            return body
        }
    }

    private class FakeLogger : Logger {
        val messages = mutableListOf<String>()
        val infoMessages = mutableListOf<String>()

        override fun d(tag: String, message: String) = Unit
        override fun i(tag: String, message: String) {
            infoMessages += "$tag $message"
        }
        override fun w(tag: String, message: String, throwable: Throwable?) {
            messages += "$tag $message"
        }
        override fun e(tag: String, message: String, throwable: Throwable?) = Unit
    }

    private companion object {
        const val BAR_LIMIT = 5
        const val DAILY_URL = "https://web.ifzq.gtimg.cn/appstock/app/newfqkline/get?param=sh600519,day,,,5,qfq"
        const val FORBIDDEN = 403
        const val TOO_MANY_REQUESTS = 429
        const val SERVER_ERROR = 500
    }
}
