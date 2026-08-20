package org.example.taximobile

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import org.example.taximobile.domain.notifications.DevicePlatform
import org.example.taximobile.feature.app.MobileAppCoordinator
import org.example.taximobile.feature.notifications.PushRegistrationRelay

/** Swift/AppDelegate bridge for APNs-backed FCM registration-token rotation. */
object IosPushRegistration {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val relay = PushRegistrationRelay(DevicePlatform.IOS)
    private var coordinator: MobileAppCoordinator? = null

    internal fun attach(coordinator: MobileAppCoordinator) {
        this.coordinator = coordinator
    }

    fun submit(registrationId: String) {
        scope.launch {
            relay.remember(registrationId)
            coordinator?.let { relay.retry(it::registerPushRegistration) }
        }
    }

    internal fun retry() {
        val activeCoordinator = coordinator ?: return
        scope.launch { relay.retry(activeCoordinator::registerPushRegistration) }
    }
}
