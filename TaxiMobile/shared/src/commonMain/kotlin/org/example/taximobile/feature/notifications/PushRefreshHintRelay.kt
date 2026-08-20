package org.example.taximobile.feature.notifications

import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.receiveAsFlow

data class PushRefreshHint(
    val eventType: String,
    val resourceId: String,
)

/**
 * Process-local handoff from platform FCM callbacks to the shared application.
 *
 * Push is only a wake-up hint. This relay validates the tiny allowlisted payload,
 * retains at most the latest hint while no screen is collecting, and never
 * interprets the resource as authoritative state. The screen responds by
 * restoring its complete backend-authorized product state.
 */
class PushRefreshHintRelay {
    private val channel = Channel<PushRefreshHint>(
        capacity = 1,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
    )

    val hints: Flow<PushRefreshHint> = channel.receiveAsFlow()

    fun submit(eventType: String?, resourceId: String?): Boolean {
        val normalizedType = eventType?.trim() ?: return false
        val normalizedResourceId = resourceId?.trim() ?: return false
        if (normalizedType !in ALLOWED_EVENT_TYPES || !RESOURCE_ID.matches(normalizedResourceId)) {
            return false
        }
        return channel.trySend(PushRefreshHint(normalizedType, normalizedResourceId)).isSuccess
    }

    private companion object {
        val ALLOWED_EVENT_TYPES = setOf(
            "RIDE_OFFER_AVAILABLE",
            "DRIVER_ASSIGNED",
            "RIDE_CANCELLED",
            "RIDE_UNMATCHED",
            "DRIVER_CREDENTIAL_EXPIRING",
            "DRIVER_CREDENTIAL_EXPIRED",
        )
        val RESOURCE_ID = Regex(
            "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$",
        )
    }
}

/** One app process has one bounded platform-to-shared refresh channel. */
object PushRefreshSignals {
    private val relay = PushRefreshHintRelay()

    val hints: Flow<PushRefreshHint> = relay.hints

    fun submit(eventType: String?, resourceId: String?): Boolean = relay.submit(eventType, resourceId)
}
