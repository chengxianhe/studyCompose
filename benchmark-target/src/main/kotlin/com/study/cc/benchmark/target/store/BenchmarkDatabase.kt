package com.study.cc.benchmark.target.store

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(entities = [PhotoMetaEntity::class], version = 1, exportSchema = true)
abstract class BenchmarkDatabase : RoomDatabase() {
    abstract fun photoMetaDao(): PhotoMetaDao

    companion object {
        fun open(context: Context, scale: Int): BenchmarkDatabase =
            Room.databaseBuilder(context, BenchmarkDatabase::class.java, fileName(scale)).build()

        fun delete(context: Context, scale: Int): Boolean = context.deleteDatabase(fileName(scale))

        private fun fileName(scale: Int) = "bench_$scale.db"
    }
}
