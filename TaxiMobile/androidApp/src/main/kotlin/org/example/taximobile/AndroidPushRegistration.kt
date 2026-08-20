package org.example.taximobile

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import org.example.taximobile.domain.notifications.DevicePlatform
import org.example.taximobile.feature.app.MobileAppCoordinator
import org.example.taximobile.feature.notifications.PushRegistrationRelay

/** Process-local bridge between Firebase token timing and authenticated sessions. */
object AndroidPushRegistration {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val relay = PushRegistrationRelay(DevicePlatform.ANDROID)

    fun submit(registrationId: String, coordinator: MobileAppCoordinator) {
        scope.launch {
            relay.remember(registrationId)
            relay.retry(coordinator::registerPushRegistration)
        }
    }

    fun retry(coordinator: MobileAppCoordinator) {
        scope.launch { relay.retry(coordinator::registerPushRegistration) }
    }
}
