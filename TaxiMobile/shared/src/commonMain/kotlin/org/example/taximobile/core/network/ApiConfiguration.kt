package org.example.taximobile.core.network

/**
 * Base configuration for the versioned backend boundary.
 *
 * Platform launch code supplies this value per build environment. It is not a
 * place for credentials or user-controlled authority.
 */
data class ApiConfiguration(val baseUrl: String) {
    init {
        require(baseUrl.startsWith("http://") || baseUrl.startsWith("https://")) {
            "API base URL must use HTTP or HTTPS."
        }
        require(!baseUrl.endsWith('/')) {
            "API base URL must not end with a slash."
        }
    }

    fun endpoint(path: String): String = "$baseUrl/api/v1/${path.removePrefix("/")}"

    fun websocketEndpoint(path: String): String = endpoint(path)
        .replaceFirst("https://", "wss://")
        .replaceFirst("http://", "ws://")
}
