package org.example.taximobile.feature.app

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.notification_driver_assigned_body
import taximobile.shared.generated.resources.notification_driver_assigned_title
import taximobile.shared.generated.resources.notification_credential_expired_body
import taximobile.shared.generated.resources.notification_credential_expired_title
import taximobile.shared.generated.resources.notification_city_authorization_title
import taximobile.shared.generated.resources.notification_city_authorization_body

class NotificationPresentationTest {
    @Test
    fun city_authorization_change_uses_current_status_refresh_copy() {
        assertEquals(
            Res.string.notification_city_authorization_title to Res.string.notification_city_authorization_body,
            notificationCopyResources("DRIVER_CITY_AUTHORIZATION_CHANGED"),
        )
    }

    @Test
    fun known_backend_event_uses_local_catalog_resources() {
        assertEquals(
            Res.string.notification_driver_assigned_title to Res.string.notification_driver_assigned_body,
            notificationCopyResources("DRIVER_ASSIGNED"),
        )
    }

    @Test
    fun unknown_backend_event_preserves_server_fallback_copy() {
        assertNull(notificationCopyResources("FUTURE_EVENT"))
    }

    @Test
    fun credential_expiry_event_uses_local_catalog_resources() {
        assertEquals(
            Res.string.notification_credential_expired_title to
                Res.string.notification_credential_expired_body,
            notificationCopyResources("DRIVER_CREDENTIAL_EXPIRED"),
        )
    }

    @Test
    fun every_launch_coordination_event_uses_reviewable_local_copy() {
        val types = listOf(
            "PASSENGER_AT_PICKUP",
            "PASSENGER_NEEDS_MORE_TIME",
            "PASSENGER_CANNOT_FIND_DRIVER",
            "DRIVER_ON_MY_WAY",
            "DRIVER_AT_PICKUP",
            "DRIVER_CANNOT_FIND_PASSENGER",
        )

        assertEquals(types.size, types.count { notificationCopyResources(it) != null })
    }

    @Test
    fun every_scheduled_delivery_event_uses_reviewable_local_copy() {
        val types = listOf(
            "SCHEDULED_OFFER",
            "SCHEDULED_DRIVER_COMMITTED",
            "SCHEDULED_DISPATCH_STARTED",
            "SCHEDULED_FALLBACK_MATCHING",
            "SCHEDULED_UNFULFILLED",
        )

        assertEquals(types.size, types.count { notificationCopyResources(it) != null })
    }
}
