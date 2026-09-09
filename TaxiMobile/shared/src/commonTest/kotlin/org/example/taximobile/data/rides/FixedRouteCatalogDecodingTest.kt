package org.example.taximobile.data.rides

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import org.example.taximobile.domain.rides.RideServiceType

class FixedRouteCatalogDecodingTest {
    @Test
    fun `public catalog preserves static direction without supply data`() {
        val response = Json { ignoreUnknownKeys = true }.decodeFromString<PublicFixedRouteCatalogResponse>(
            """{
              "city":{"id":"city-1","code":"RABAT","localized_name":{"en":"Rabat","fr":"Rabat","ar":"الرباط"},"timezone":"Africa/Casablanca","lifecycle_status":"ACTIVE","booking_available":true},
              "routes":[{"id":"route-1","code":"RABAT_01","status":"ACTIVE","versions":[{
                "id":"version-1","localized_name":{"en":"Station to university","fr":"Gare vers université","ar":"المحطة إلى الجامعة"},
                "directions":[{"id":"direction-1","direction_code":"OUTBOUND",
                  "start_location_name":{"en":"Station","fr":"Gare","ar":"المحطة"},
                  "finish_location_name":{"en":"University","fr":"Université","ar":"الجامعة"},
                  "start":{"latitude":34.02,"longitude":-6.84},"finish":{"latitude":34.00,"longitude":-6.80},
                  "geometry":{"type":"LineString","coordinates":[[-6.84,34.02],[-6.82,34.01],[-6.80,34.00]]},
                  "flat_fare":"8.00","currency":"MAD","immediate_booking_enabled":true,
                  "scheduled_booking_enabled":false,"stops":[]
                }]
              }]}]
            }"""
        )

        val catalog = response.toDomain()
        val direction = catalog.directions.single()
        assertEquals("RABAT_01", direction.routeCode)
        assertEquals("Station", direction.startName.en)
        assertEquals("University", direction.finishName.en)
        assertEquals("8.00", direction.flatFare)
        assertEquals(3, direction.geometry.size)
        assertTrue(direction.immediateBookingEnabled)
        assertFalse(direction.scheduledBookingEnabled)
    }

    @Test
    fun `ride history retains fixed-route service and direction identity`() {
        val response = Json { ignoreUnknownKeys = true }.decodeFromString<RideListResponse>(
            """{"items":[{
              "id":"ride-1","status":"MATCHING","service_type":"FIXED_ROUTE",
              "pickup":{"latitude":34.02,"longitude":-6.84},
              "destination":{"latitude":34.00,"longitude":-6.80},"payment_method":"CASH",
              "fixed_route":{"direction_version_id":"direction-1","route_version_id":"version-1",
                "route_code":"RABAT_01","localized_route_name":{"en":"Route","fr":"Ligne","ar":"الخط"},
                "direction_code":"OUTBOUND","start_location_name":{"en":"Station","fr":"Gare","ar":"المحطة"},
                "finish_location_name":{"en":"University","fr":"Université","ar":"الجامعة"}}
            }]}"""
        )

        val ride = response.items.single().toSummary()
        assertEquals(RideServiceType.FIXED_ROUTE, ride.serviceType)
        assertEquals("direction-1", ride.fixedRoute?.directionVersionId)
    }
}
