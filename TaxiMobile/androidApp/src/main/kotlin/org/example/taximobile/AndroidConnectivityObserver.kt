package org.example.taximobile

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import org.example.taximobile.feature.connectivity.ConnectivityObserver
import org.example.taximobile.feature.connectivity.ConnectivityStatus

/** Android's validated default network exposed as a coarse recovery hint. */
class AndroidConnectivityObserver(context: Context) : ConnectivityObserver {
    private val connectivityManager = context.applicationContext
        .getSystemService(ConnectivityManager::class.java)
    private val mutableStatus = MutableStateFlow(currentStatus())
    private var closed = false

    override val status: StateFlow<ConnectivityStatus> = mutableStatus.asStateFlow()

    private val callback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) = publishCurrentStatus()

        override fun onLost(network: Network) = publishCurrentStatus()

        override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) =
            publishCurrentStatus()
    }

    init {
        connectivityManager.registerDefaultNetworkCallback(callback)
        publishCurrentStatus()
    }

    private fun publishCurrentStatus() {
        mutableStatus.value = currentStatus()
    }

    private fun currentStatus(): ConnectivityStatus {
        val network = connectivityManager.activeNetwork ?: return ConnectivityStatus.UNAVAILABLE
        val capabilities = connectivityManager.getNetworkCapabilities(network)
            ?: return ConnectivityStatus.UNAVAILABLE
        return if (
            capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
            capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
        ) {
            ConnectivityStatus.AVAILABLE
        } else {
            ConnectivityStatus.UNAVAILABLE
        }
    }

    override fun close() {
        if (closed) return
        closed = true
        connectivityManager.unregisterNetworkCallback(callback)
    }
}
