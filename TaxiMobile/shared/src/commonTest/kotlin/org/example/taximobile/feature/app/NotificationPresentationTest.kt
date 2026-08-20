package org.example.taximobile.feature.app

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.notification_driver_assigned_body
import taximobile.shared.generated.resources.notification_driver_assigned_title
import taximobile.shared.generated.resources.notification_credential_expired_body
import taximobile.shared.generated.resources.notification_credential_expired_title

class NotificationPresentationTest {
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
}
