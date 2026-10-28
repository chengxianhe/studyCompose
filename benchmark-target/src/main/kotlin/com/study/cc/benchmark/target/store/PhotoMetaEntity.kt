package com.study.cc.benchmark.target.store

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * 与 T-012 计划同形状的轻量元数据原型。`takenAtUtcMs == 0` 且 `localYear == 0` 表示「未知日期」。
 *
 * 两个索引都带上 `takenAtUtcMs`，让年 / 月 / 日汇总与「历史上的今天」可以只扫索引（covering），
 * 不回表；`id` 是 rowid，天然在索引里。
 */
@Entity(
    tableName = "photo_meta",
    indices = [
        Index(value = ["localYear", "localMonth", "localDay", "takenAtUtcMs"]),
        Index(value = ["localMonth", "localDay", "localYear", "takenAtUtcMs"]),
        Index(value = ["bucketId"]),
    ],
)
data class PhotoMetaEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val takenAtUtcMs: Long,
    val localYear: Int,
    val localMonth: Int,
    val localDay: Int,
    val mediaType: Int,
    val bucketId: Long,
)
