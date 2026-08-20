package org.example.taximobile.domain.notifications

/** Server-created notification history; payload IDs are never treated as state. */
data class AppNotification(
    val id: String,
    val type: String,
    val fallbackTitle: String,
    val fallbackBody: String,
    val read: Boolean,
)

interface NotificationGateway {
    suspend fun list(): List<AppNotification>
    suspend fun markRead(id: String): AppNotification
    suspend fun registerDevice(registrationId: String, platform: DevicePlatform)
    suspend fun unregisterDevice(registrationId: String, platform: DevicePlatform)
}

enum class DevicePlatform { ANDROID, IOS }
