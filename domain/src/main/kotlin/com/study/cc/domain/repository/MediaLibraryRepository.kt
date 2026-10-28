package com.study.cc.domain.repository

import com.study.cc.domain.model.LibrarySyncState
import kotlinx.coroutines.flow.Flow

interface MediaLibraryRepository {
    /** 首次收集时才开始监听系统媒体库并同步；同步在后台进行，不阻塞收集方。 */
    fun observeSyncState(): Flow<LibrarySyncState>

    /** 重新评估授权并立刻安排一次同步，例如用户刚刚改了授权。 */
    suspend fun refresh()
}
