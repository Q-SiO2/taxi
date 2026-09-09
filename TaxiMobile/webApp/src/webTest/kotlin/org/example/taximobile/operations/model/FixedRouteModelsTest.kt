package org.example.taximobile.operations.model

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class FixedRouteModelsTest {
    @Test
    fun publishedDirectionPreservesOrderedTextFareAndGeometry() {
        val version = Json { ignoreUnknownKeys = true }.decodeFromString<FixedRouteVersionRecord>(
            """{
              "id":"version-1","fixed_route_id":"route-1","route_code":"RABAT_01",
              "city_id":"city-1","operator_id":"operator-1","version":"v1",
              "localized_name":{"en":"Station to university","fr":"Gare vers université","ar":"المحطة إلى الجامعة"},
              "localized_description":{},"status":"PUBLISHED",
              "effective_from":"2026-08-27T12:00:00Z","optimistic_version":3,
              "directions":[{
                "id":"direction-1","direction_code":"OUTBOUND",
                "start_location_name":{"en":"Station","fr":"Gare","ar":"المحطة"},
                "finish_location_name":{"en":"University","fr":"Université","ar":"الجامعة"},
                "start":{"latitude":34.02,"longitude":-6.84},
                "finish":{"latitude":34.00,"longitude":-6.80},
                "geometry":{"type":"LineString","coordinates":[[-6.84,34.02],[-6.80,34.00]]},
                "flat_fare_policy_version_id":"fare-1","flat_fare":"8.00","currency":"MAD",
                "immediate_booking_enabled":true,"scheduled_booking_enabled":false,"stops":[]
              }]
            }"""
        )

        val direction = version.directions.single()
        assertEquals("Station", direction.startLocationName.en)
        assertEquals("University", direction.finishLocationName.en)
        assertEquals("8.00", direction.flatFare)
        assertEquals(2, direction.geometry.coordinates.size)
    }

    @Test
    fun draftDirectionCanPreserveGeometryBeforeFareIsLinked() {
        val version = Json { ignoreUnknownKeys = true }.decodeFromString<FixedRouteVersionRecord>(
            """{
              "id":"version-2","fixed_route_id":"route-2","route_code":"RABAT_02",
              "city_id":"city-1","operator_id":"operator-1","version":"draft-v1",
              "localized_name":{"en":"Old town to business district","fr":"Médina vers quartier d'affaires","ar":"المدينة القديمة إلى حي الأعمال"},
              "localized_description":{},"status":"DRAFT",
              "effective_from":"2026-08-27T12:00:00Z","optimistic_version":1,
              "directions":[{
                "id":"direction-2","direction_code":"OUTBOUND",
                "start_location_name":{"en":"Old town","fr":"Médina","ar":"المدينة القديمة"},
                "finish_location_name":{"en":"Business district","fr":"Quartier d'affaires","ar":"حي الأعمال"},
                "start":{"latitude":34.03,"longitude":-6.85},
                "finish":{"latitude":33.99,"longitude":-6.77},
                "geometry":{"type":"LineString","coordinates":[[-6.85,34.03],[-6.77,33.99]]},
                "flat_fare_policy_version_id":null,"flat_fare":null,"currency":null,
                "immediate_booking_enabled":false,"scheduled_booking_enabled":false,"stops":[]
              }]
            }"""
        )

        val direction = version.directions.single()
        assertNull(direction.flatFarePolicyVersionId)
        assertNull(direction.flatFare)
        assertNull(direction.currency)
        assertEquals(2, direction.geometry.coordinates.size)
    }

    @Test
    fun routeValidationAndTransitionsFailClosed() {
        assertTrue(validRouteCode("RABAT_01"))
        assertFalse(validRouteCode("rabat route"))
        assertTrue(validLatitude("34.02"))
        assertFalse(validLatitude("91"))
        assertTrue(validLongitude("-6.84"))
        assertFalse(validLongitude("-181"))
        assertEquals("IN_REVIEW", fixedRouteTargetFor("DRAFT"))
        assertEquals("PUBLISHED", fixedRouteTargetFor("IN_REVIEW"))
        assertNull(fixedRouteTargetFor("PUBLISHED"))
    }
}
