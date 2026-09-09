package org.example.taximobile.operations.model

import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class CityAuthorizationModelsTest {
    @Test
    fun reinstatementIsOfferedOnlyForSuspension() {
        assertTrue(CityAuthorizationAction.REINSTATE in cityAuthorizationActions("SUSPENDED"))
        listOf("ACTIVE", "EXPIRED", "REVOKED", "UNKNOWN").forEach {
            assertFalse(CityAuthorizationAction.REINSTATE in cityAuthorizationActions(it))
        }
        assertTrue(cityAuthorizationActions("REVOKED").isEmpty())
        assertTrue(cityAuthorizationActions("UNKNOWN").isEmpty())
    }

    @Test
    fun commandBindsReviewedApplicationVersionWithoutExpiryOrScopeAuthority() {
        val encoded = Json.encodeToString(CityAuthorizationDecisionRequest(7, "SUSPEND", "ELIGIBILITY_REVIEW"))
        assertEquals("{\"expected_application_version\":7,\"action\":\"SUSPEND\",\"reason_code\":\"ELIGIBILITY_REVIEW\"}", encoded)
    }
}
