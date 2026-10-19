package com.study.cc.data.stock

import java.nio.charset.Charset

internal fun fixture(name: String, charset: Charset = Charsets.UTF_8): String =
    requireNotNull(StockFixtures::class.java.getResourceAsStream("/stock/tencent/$name"))
        .use { it.readBytes().toString(charset) }

private object StockFixtures
