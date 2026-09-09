package org.example.taximobile.feature.driver.onboarding

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotEquals
import taximobile.shared.generated.resources.*

class CityAuthorizationPresentationTest {
    @Test
    fun restrictionsCannotUseTheActiveAuthorizationLabel() {
        val active = cityAuthorizationStatusResource("ACTIVE")
        assertEquals(Res.string.city_authorization_active, active)
        assertEquals(Res.string.city_authorization_suspended, cityAuthorizationStatusResource("SUSPENDED"))
        assertEquals(Res.string.city_authorization_expired, cityAuthorizationStatusResource("EXPIRED"))
        assertEquals(Res.string.city_authorization_revoked, cityAuthorizationStatusResource("REVOKED"))
        listOf("SUSPENDED", "EXPIRED", "REVOKED").forEach {
            assertNotEquals(active, cityAuthorizationStatusResource(it))
        }
    }

    @Test
    fun absentOrUnexpectedStatusIsUnavailableInsteadOfApproved() {
        listOf("", "APPROVED", "active", "UNKNOWN").forEach {
            assertEquals(Res.string.city_authorization_unknown, cityAuthorizationStatusResource(it))
        }
    }
}
