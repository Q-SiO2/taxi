package org.example.taximobile

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import org.example.taximobile.feature.connectivity.ConnectivityObserver
import org.example.taximobile.feature.connectivity.ConnectivityStatus
import platform.Network.nw_path_get_status
import platform.Network.nw_path_monitor_cancel
import platform.Network.nw_path_monitor_create
import platform.Network.nw_path_monitor_set_queue
import platform.Network.nw_path_monitor_set_update_handler
import platform.Network.nw_path_monitor_start
import platform.Network.nw_path_status_satisfied
import platform.darwin.dispatch_get_main_queue

/** Apple's path monitor exposed as the same coarse recovery hint as Android. */
class IosConnectivityObserver : ConnectivityObserver {
    private val monitor = nw_path_monitor_create()
    private val mutableStatus = MutableStateFlow(ConnectivityStatus.UNKNOWN)
    private var closed = false

    override val status: StateFlow<ConnectivityStatus> = mutableStatus.asStateFlow()

    init {
        nw_path_monitor_set_update_handler(monitor) { path ->
            mutableStatus.value = if (nw_path_get_status(path) == nw_path_status_satisfied) {
                ConnectivityStatus.AVAILABLE
            } else {
                ConnectivityStatus.UNAVAILABLE
            }
        }
        nw_path_monitor_set_queue(monitor, dispatch_get_main_queue())
        nw_path_monitor_start(monitor)
    }

    override fun close() {
        if (closed) return
        closed = true
        nw_path_monitor_cancel(monitor)
    }
}
