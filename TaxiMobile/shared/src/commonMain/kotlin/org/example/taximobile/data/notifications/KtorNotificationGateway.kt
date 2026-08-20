package org.example.taximobile.data.notifications

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.delete
import io.ktor.client.request.post
import io.ktor.client.request.header
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.isSuccess
import io.ktor.http.contentType
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.notifications.AppNotification
import org.example.taximobile.domain.notifications.NotificationGateway
import org.example.taximobile.domain.notifications.DevicePlatform

class KtorNotificationGateway(private val client: HttpClient, private val api: ApiConfiguration, private val accessToken: suspend () -> String) : NotificationGateway {
    override suspend fun list(): List<AppNotification> = request {
        val response = client.get(api.endpoint("notifications")) { header(HttpHeaders.Authorization, "Bearer ${accessToken()}") }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not load notifications.")
        response.body<NotificationListResponse>().items.map { it.toDomain() }
    }

    override suspend fun markRead(id: String): AppNotification = request {
        val response = client.post(api.endpoint("notifications/$id/read")) { header(HttpHeaders.Authorization, "Bearer ${accessToken()}") }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not mark this notification read.")
        response.body<NotificationResponse>().toDomain()
    }

    override suspend fun registerDevice(registrationId: String, platform: DevicePlatform) = request {
        val response = client.post(api.endpoint("devices")) {
            header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
            contentType(ContentType.Application.Json)
            setBody(DeviceRegistrationRequest(platform.name, registrationId = registrationId))
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not register push delivery.")
    }

    override suspend fun unregisterDevice(registrationId: String, platform: DevicePlatform) = request {
        val response = client.delete(api.endpoint("devices")) {
            header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
            contentType(ContentType.Application.Json)
            setBody(DeviceRegistrationRequest(platform.name, registrationId = registrationId))
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) throw ApiRequestException(response.status.value, "The server could not revoke push delivery.")
    }

    private suspend fun <T> request(block: suspend () -> T): T = try { block() } catch (error: AuthenticationRejectedException) { throw error } catch (error: ApiRequestException) { throw error } catch (_: Exception) { throw AuthenticationNetworkException() }
}

@Serializable private data class NotificationListResponse(val items: List<NotificationResponse>)
@Serializable
private data class NotificationResponse(
    val id: String,
    val type: String,
    val title: String,
    val body: String,
    @SerialName("read_at") val readAt: String? = null,
) {
    fun toDomain() = AppNotification(
        id = id,
        type = type,
        fallbackTitle = title,
        fallbackBody = body,
        read = readAt != null,
    )
}
@Serializable
private data class DeviceRegistrationRequest(
    val platform: String,
    @SerialName("registration_kind") val registrationKind: String = "FIREBASE_INSTALLATION_ID",
    @SerialName("registration_id") val registrationId: String,
)
