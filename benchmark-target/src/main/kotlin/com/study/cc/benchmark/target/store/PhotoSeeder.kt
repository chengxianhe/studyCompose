package com.study.cc.benchmark.target.store

import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteStatement

private const val BATCH_SIZE = 10_000
private const val INSERT_SQL =
    "INSERT INTO photo_meta (takenAtUtcMs, localYear, localMonth, localDay, mediaType, bucketId) " +
        "VALUES (?, ?, ?, ?, ?, ?)"
private const val COL_TAKEN_AT = 1
private const val COL_YEAR = 2
private const val COL_MONTH = 3
private const val COL_DAY = 4
private const val COL_MEDIA = 5
private const val COL_BUCKET = 6

/** 用预编译语句分批事务写入，写入耗时就是 T-012 首次全量同步预算的参照。 */
class PhotoSeeder(private val database: BenchmarkDatabase) {
    fun seed(config: GeneratorConfig) {
        val sqlite = database.openHelper.writableDatabase
        SyntheticPhotoGenerator(config).rows().chunked(BATCH_SIZE).forEach { batch -> insertBatch(sqlite, batch) }
    }

    private fun insertBatch(sqlite: SupportSQLiteDatabase, batch: List<PhotoMetaEntity>) {
        sqlite.beginTransaction()
        try {
            val statement = sqlite.compileStatement(INSERT_SQL)
            batch.forEach { row -> statement.insertRow(row) }
            statement.close()
            sqlite.setTransactionSuccessful()
        } finally {
            sqlite.endTransaction()
        }
    }

    private fun SupportSQLiteStatement.insertRow(row: PhotoMetaEntity) {
        bindLong(COL_TAKEN_AT, row.takenAtUtcMs)
        bindLong(COL_YEAR, row.localYear.toLong())
        bindLong(COL_MONTH, row.localMonth.toLong())
        bindLong(COL_DAY, row.localDay.toLong())
        bindLong(COL_MEDIA, row.mediaType.toLong())
        bindLong(COL_BUCKET, row.bucketId)
        executeInsert()
    }
}
