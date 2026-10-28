package com.study.cc.data.di

import javax.inject.Qualifier

/** Application-wide scope: a sync must not be cancelled when the UI goes away. */
@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class MediaSyncScope
