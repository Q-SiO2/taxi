package org.example.taximobile.application

import kotlinx.browser.window

data class OperationsEnvironment(
    val apiBaseUrl: String,
    val isLocalDevelopment: Boolean,
) {
    companion object {
        /**
         * Local webpack development talks to the backend on port 8000. A hosted
         * build uses the current HTTPS origin and expects `/api/v1` to be reverse
         * proxied to the API. No credential or bearer token is read from browser
         * storage or URL parameters.
         */
        fun fromBrowser(): OperationsEnvironment {
            val hostname = window.location.hostname.lowercase()
            val local = hostname == "localhost" || hostname == "127.0.0.1" || hostname == "[::1]"
            val baseUrl = if (local) {
                "http://$hostname:8000/api/v1"
            } else {
                "${window.location.origin.trimEnd('/')}/api/v1"
            }
            return OperationsEnvironment(
                apiBaseUrl = baseUrl,
                isLocalDevelopment = local,
            )
        }
    }
}
