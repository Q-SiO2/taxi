package org.example.taximobile.operations.data

private const val OPERATIONS_API_PREFIX = "/api/v1"

/**
 * Single URL-construction boundary for the browser operations console.
 *
 * [apiBaseUrl] is supplied by [OperationsEnvironment][org.example.taximobile.application.OperationsEnvironment]
 * and already includes the version prefix. Keeping that contract here prevents
 * individual gateways from accidentally producing `/api/v1/api/v1/...` URLs.
 */
internal class OperationsApiEndpoints(apiBaseUrl: String) {
    private val baseUrl = apiBaseUrl.trimEnd('/').also { candidate ->
        require(candidate.startsWith("http://") || candidate.startsWith("https://")) {
            "The operations API base URL must use HTTP or HTTPS."
        }
        require('?' !in candidate && '#' !in candidate) {
            "The operations API base URL must not contain a query or fragment."
        }
        require(candidate.endsWith(OPERATIONS_API_PREFIX)) {
            "The operations API base URL must end with $OPERATIONS_API_PREFIX."
        }
        require(!candidate.removeSuffix(OPERATIONS_API_PREFIX).endsWith(OPERATIONS_API_PREFIX)) {
            "The operations API base URL contains the version prefix twice."
        }
    }

    fun url(path: String): String {
        require(path.isNotBlank()) { "An operations API path is required." }
        require(!path.startsWith('/')) { "Operations API paths must be relative." }
        require('?' !in path && '#' !in path && "//" !in path) {
            "Operations API paths must not contain queries, fragments, or empty segments."
        }
        return "$baseUrl/$path"
    }
}
