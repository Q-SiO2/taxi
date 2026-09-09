package org.example.taximobile.operations.model

import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class ControlPlaneModelsTest {
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    @Test
    fun `boundary parser validates coordinates and closes polygon`() {
        val result = parseServiceAreaBoundary(
            """
            -7.70,33.50
            -7.50,33.50
            -7.50,33.65
            -7.70,33.65
            """.trimIndent()
        )

        val boundary = assertNotNull(result.boundary)
        val ring = boundary.coordinates.single().single()
        assertEquals("MultiPolygon", boundary.type)
        assertEquals(5, ring.size)
        assertEquals(ring.first(), ring.last())
        assertNull(result.error)
    }

    @Test
    fun `boundary parser rejects malformed degenerate and out of range input`() {
        assertNotNull(parseServiceAreaBoundary("-7.7,33.5\n-7.5,33.5").error)
        assertNotNull(parseServiceAreaBoundary("-7.7,33.5\n-7.6,33.5\n-7.5,33.5").error)
        assertNotNull(parseServiceAreaBoundary("-181,33.5\n-7.6,33.6\n-7.5,33.5").error)
        assertNotNull(parseServiceAreaBoundary("longitude,latitude\n-7.6,33.6\n-7.5,33.5").error)
    }

    @Test
    fun `control plane transitions fail closed`() {
        assertEquals(listOf("ACTIVE", "INACTIVE"), operatorStatusTargetsFor("DRAFT"))
        assertEquals(listOf("INACTIVE"), operatorStatusTargetsFor("ACTIVE"))
        assertEquals(listOf("ACTIVE"), operatorStatusTargetsFor("INACTIVE"))
        assertTrue(operatorStatusTargetsFor("RETIRED").isEmpty())
        assertEquals("IN_REVIEW", serviceAreaTargetFor("DRAFT"))
        assertEquals("APPROVED", serviceAreaTargetFor("IN_REVIEW"))
        assertNull(serviceAreaTargetFor("APPROVED"))
        assertEquals("ACTIVE", configurationTargetFor("APPROVED"))
        assertNull(configurationTargetFor("ACTIVE"))
        assertTrue(validControlPlaneVersion("casablanca-pilot_v1"))
        assertFalse(validControlPlaneVersion("bad version"))
        assertTrue(validControlPlaneEffectiveRange("2026-09-01T00:00Z", ""))
        assertTrue(validControlPlaneEffectiveRange("2026-09-01T00:00:00Z", "2027-09-01T00:00:00Z"))
        assertFalse(validControlPlaneEffectiveRange("2026-09-01T00:00:00Z", "2025-09-01T00:00:00Z"))
    }

    @Test
    fun `configuration request serializes authoritative component references`() {
        val request = CityConfigurationCreateRequest(
            version = "pilot-v1",
            serviceAreaVersionId = "area-1",
            driverRequirementVersionId = "requirements-1",
            services = listOf(
                ConfigurationServiceInput(
                    serviceType = "ON_DEMAND",
                    operatorCityAssignmentId = "assignment-1",
                    tariffVersionId = "tariff-1",
                    operatorFeePolicyVersionId = "fee-1",
                    schedulingPolicyVersionId = "schedule-1",
                    paymentCapabilityVersionId = "payment-1",
                )
            ),
            routes = listOf(ConfigurationRouteInput("route-version-1", true, false)),
        )

        val encoded = json.encodeToString(request)

        assertTrue("\"service_area_version_id\":\"area-1\"" in encoded)
        assertTrue("\"driver_requirement_version_id\":\"requirements-1\"" in encoded)
        assertTrue("\"payment_capability_version_id\":\"payment-1\"" in encoded)
        assertTrue("\"fixed_route_version_id\":\"route-version-1\"" in encoded)
    }

    @Test
    fun `configuration response decodes routes and driver requirement provenance`() {
        val configuration = json.decodeFromString<CityConfigurationRecord>(
            """{
              "id":"configuration-1","city_id":"city-1","version":"pilot-v1","status":"APPROVED",
              "service_area_version_id":"area-1","driver_requirement_version_id":"requirements-1",
              "optimistic_version":3,
              "services":[{"service_type":"FIXED_ROUTE","operator_city_assignment_id":"assignment-1",
                "operator_fee_policy_version_id":"fee-1","payment_capability_version_id":"payment-1","enabled":true}],
              "routes":[{"fixed_route_version_id":"route-version-1","immediate_booking_enabled":true,
                "scheduled_booking_enabled":false}],
              "readiness_checks":[],"missing_readiness_gates":[],"missing_pilot_entry_gates":[],
              "missing_public_activation_gates":[],"post_launch_review_status":"PENDING",
              "created_at":"2026-08-31T10:00:00Z","updated_at":"2026-08-31T10:00:00Z"
            }"""
        )

        assertEquals("requirements-1", configuration.driverRequirementVersionId)
        assertEquals("payment-1", configuration.services.single().paymentCapabilityVersionId)
        assertEquals("route-version-1", configuration.routes.single().fixedRouteVersionId)
    }
}
