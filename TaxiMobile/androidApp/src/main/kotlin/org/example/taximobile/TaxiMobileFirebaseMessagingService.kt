package org.example.taximobile

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import org.example.taximobile.app.AppRole
import org.example.taximobile.feature.notifications.PushRefreshSignals

/**
 * Firebase installation registration is submitted to TaxiMobile's authenticated device endpoint.
 * Incoming data messages intentionally contain only refresh identifiers; the
 * normal REST/WebSocket refresh path remains authoritative.
 */
class TaxiMobileFirebaseMessagingService : FirebaseMessagingService() {
    override fun onRegistered(installationId: String) {
        val role = AppRole.valueOf(BuildConfig.APP_ROLE)
        AndroidPushRegistration.submit(
            registrationId = installationId,
            coordinator = AndroidAppDependencies(applicationContext, role).appCoordinator,
        )
    }

    override fun onMessageReceived(message: RemoteMessage) {
        // Unknown, malformed, or expanded provider payloads are ignored. The
        // relay never mutates a ride; an active screen reloads through REST.
        PushRefreshSignals.submit(
            eventType = message.data["type"],
            resourceId = message.data["resource_id"],
        )
    }
}
