package org.example.taximobile.operations.data

import org.example.taximobile.operations.model.OperationsTokens

/** Existing one-refresh protocol shared by authenticated reads, writes and logout. */
internal suspend fun <T> withOperationsAccessRefresh(
    active: OperationsTokens,
    refresh: suspend (String?, String?) -> OperationsTokens,
    publish: (OperationsTokens) -> Unit,
    request: suspend (String) -> T,
): T = try {
    request(active.accessToken)
} catch (error: OperationsApiException) {
    if (error.statusCode != 401) throw error
    val refreshed = refresh(active.refreshToken, active.csrfToken)
    // Publish a consumed rotation even if the retried command is rejected.
    publish(refreshed)
    request(refreshed.accessToken)
}
