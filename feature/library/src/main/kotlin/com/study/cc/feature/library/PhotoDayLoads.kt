package com.study.cc.feature.library

import com.study.cc.core.logging.Logger
import com.study.cc.domain.model.PhotoDay
import com.study.cc.domain.model.PhotoMedia
import com.study.cc.domain.model.PhotoScope
import com.study.cc.domain.usecase.GetPhotoDayItemsUseCase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.onCompletion
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.job
import kotlinx.coroutines.launch

private const val MAX_CACHED_DAYS = 12
private const val TAG = "PhotoDayLoads"

internal data class PhotoDayLoadState(
    val items: Map<PhotoDay, List<PhotoMedia>> = emptyMap(),
    val loading: Set<PhotoDay> = emptySet(),
    val failed: Boolean = false,
)

/** Owns only viewport requests and their cache. All access runs on the ViewModel scope dispatcher. */
internal class PhotoDayLoads(
    private val scope: CoroutineScope,
    private val getItems: GetPhotoDayItemsUseCase,
    private val logger: Logger,
) {
    private val mutableState = MutableStateFlow(PhotoDayLoadState())
    val state = mutableState.asStateFlow()
    private val requests = mutableMapOf<PhotoDay, Job>()
    private val recent = ArrayDeque<PhotoDay>()
    private var visible = emptySet<PhotoDay>()
    private var available = emptySet<PhotoDay>()

    fun updateBuckets(days: Set<PhotoDay>) {
        available = days
        val oldRequests = requests.values.toList()
        requests.clear()
        oldRequests.forEach { it.cancel() }
        recent.clear()
        mutableState.value = PhotoDayLoadState()
        updateVisible(visible.intersect(days))
    }

    fun updateVisible(days: Set<PhotoDay>) {
        visible = days.intersect(available)
        (requests.keys - visible).forEach { day -> requests.remove(day)?.cancel() }
        mutableState.update { it.copy(loading = requests.keys.toSet()) }
        visible.forEach { day ->
            if (day in mutableState.value.items) {
                recent.remove(day)
                recent.addLast(day)
            } else if (day !in requests && !mutableState.value.failed) {
                load(day)
            }
        }
        trimCache()
    }

    fun retry() {
        mutableState.update { it.copy(failed = false) }
        updateVisible(visible)
    }

    private fun load(day: PhotoDay) {
        val request = scope.launch(start = CoroutineStart.LAZY) {
            val identity = currentCoroutineContext().job
            flow { emit(getItems(PhotoScope.All, day)) }.onEach { items ->
                if (requests[day] === identity) {
                    recent.remove(day)
                    recent.addLast(day)
                    mutableState.update { it.copy(items = it.items + (day to items)) }
                    trimCache()
                }
            }.catch { error ->
                logger.e(TAG, "day item query failed", error)
                if (requests[day] === identity) mutableState.update { it.copy(failed = true) }
            }.onCompletion {
                if (requests[day] === identity) {
                    requests.remove(day)
                    mutableState.update { it.copy(loading = requests.keys.toSet()) }
                }
            }.collect {}
        }
        requests[day] = request
        mutableState.update { it.copy(loading = requests.keys.toSet()) }
        request.start()
    }

    private fun trimCache() {
        val items = mutableState.value.items.toMutableMap()
        val limit = maxOf(MAX_CACHED_DAYS, visible.size)
        while (items.size > limit) {
            val oldest = recent.firstOrNull { it !in visible } ?: break
            recent.remove(oldest)
            items.remove(oldest)
        }
        mutableState.update { it.copy(items = items) }
    }
}
