package com.study.cc.data.repository

import com.study.cc.core.logging.Logger
import com.study.cc.data.stock.TencentApi
import com.study.cc.data.stock.TencentUrls
import com.study.cc.data.stock.parseTencentDailyBars
import com.study.cc.data.stock.parseTencentQuote
import com.study.cc.data.stock.parseTencentSearch
import com.study.cc.domain.model.DailyBars
import com.study.cc.domain.model.Quote
import com.study.cc.domain.model.SecurityId
import com.study.cc.domain.model.SecuritySummary
import com.study.cc.domain.model.StockDataException
import com.study.cc.domain.repository.StockMarketRepository
import kotlinx.coroutines.CancellationException
import retrofit2.HttpException
import java.io.IOException
import java.nio.charset.Charset
import java.nio.charset.StandardCharsets
import java.time.Clock
import javax.inject.Inject

internal class StockMarketRepositoryImpl @Inject constructor(
    private val api: TencentApi,
    private val clock: Clock,
    private val logger: Logger,
) : StockMarketRepository {
    override suspend fun searchSecurities(query: String): List<SecuritySummary> = fetch(null) {
        val results = parseTencentSearch(api.get(TencentUrls.search(query)).bytes().toString(StandardCharsets.UTF_8))
        logger.i(TAG, "searchSecurities ok count=${results.size}")
        results
    }

    override suspend fun getQuote(security: SecurityId): Quote = fetch(security) {
        val quote = parseTencentQuote(
            api.get(TencentUrls.quote(security)).bytes().toString(GBK),
            security,
            clock.instant(),
        )
        logger.i(TAG, "getQuote ok ${security.code}")
        quote
    }

    override suspend fun getDailyBars(security: SecurityId, limit: Int): DailyBars = fetch(security) {
        val bars = parseTencentDailyBars(
            api.get(TencentUrls.daily(security, limit)).bytes().toString(StandardCharsets.UTF_8),
            security,
            clock.instant(),
        )
        logger.i(TAG, "getDailyBars ok ${security.code} count=${bars.bars.size}")
        bars
    }

    private suspend fun <T> fetch(security: SecurityId?, action: suspend () -> T): T = try {
        action()
    } catch (e: CancellationException) {
        throw e
    } catch (e: IOException) {
        failure(StockDataException.UpstreamUnavailable(cause = e), security)
    } catch (e: HttpException) {
        failure(StockDataException.UpstreamUnavailable(cause = e), security)
    } catch (e: StockDataException) {
        failure(e, security)
    }

    private fun failure(error: StockDataException, security: SecurityId?): Nothing {
        logger.w(TAG, "${error.javaClass.simpleName} ${security?.code.orEmpty()}")
        throw error
    }

    private companion object {
        const val TAG = "StockMarketRepositoryImpl"
        val GBK: Charset = Charset.forName("GBK")
    }
}
