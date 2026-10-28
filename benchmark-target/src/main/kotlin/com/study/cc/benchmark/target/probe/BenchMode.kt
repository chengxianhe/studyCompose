package com.study.cc.benchmark.target.probe

const val EXTRA_MODE = "mode"
const val EXTRA_SCALE = "scale"
const val DEFAULT_SCALE = 1_000_000

/** 由 Macrobenchmark 通过 Intent extra 选择本次要跑什么。 */
enum class BenchMode(val key: String) {
    /** 库不存在或行数不对才生成。 */
    SEED("seed"),

    /** 先删库再生成，用来度量首次全量灌入耗时。 */
    RESEED("reseed"),
    GRID("grid"),
    QUERIES("queries"),
    LONG_ARRAYS("longarrays"),
    ;

    companion object {
        fun from(key: String?): BenchMode = entries.firstOrNull { it.key == key } ?: GRID
    }
}
