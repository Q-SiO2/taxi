package org.example.taximobile.feature.notifications

import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.example.taximobile.domain.notifications.DevicePlatform

/**
 * Holds the latest Firebase installation ID only for this app process.
 *
 * Firebase may register before TaxiMobile has an authenticated session. The
 * relay keeps the latest ID so every successful login or restore can retry the
 * authenticated `/devices` call. It remains available after success because a
 * later account on the same process must transfer the installation ownership.
 */
class PushRegistrationRelay(private val platform: DevicePlatform) {
    private val mutex = Mutex()
    private var latestRegistrationId: String? = null

    suspend fun remember(registrationId: String) {
        val normalized = registrationId.trim()
        if (normalized.isEmpty()) return
        mutex.withLock { latestRegistrationId = normalized }
    }

    suspend fun retry(
        register: suspend (registrationId: String, platform: DevicePlatform) -> Boolean,
    ): Boolean {
        val registrationId = mutex.withLock { latestRegistrationId } ?: return false
        return register(registrationId, platform)
    }
}
