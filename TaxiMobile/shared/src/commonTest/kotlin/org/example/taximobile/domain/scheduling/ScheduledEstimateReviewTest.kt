package org.example.taximobile.domain.scheduling

import org.example.taximobile.data.scheduling.bookingFixture
import org.example.taximobile.domain.rides.Coordinates
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class ScheduledEstimateReviewTest {
    private fun point() = bookingFixture().let { b -> ScheduledBookingEstimate(
        b.cityId, b.operatorId, "ON_DEMAND", null, b.scheduledFor, b.cityTimezone,
        b.pickup, b.destination, b.economics, b.cancellationTerms, "CASH",
    ) }

    @Test fun point_review_matches_the_instant_city_and_exact_coordinate_pair() {
        val q = point()
        assertTrue(q.matchesPointRequest(q.scheduledFor, q.cityId, q.pickup, q.destination))
        assertTrue(q.matchesPointRequest("2026-11-01T09:30:00+01:00", null,
            q.pickup.copy(address = "Normalized label"), q.destination))
        assertFalse(q.matchesPointRequest("2026-11-02T08:30:00Z", q.cityId, q.pickup, q.destination))
        assertFalse(q.matchesPointRequest(q.scheduledFor, "other-city", q.pickup, q.destination))
        assertFalse(q.matchesPointRequest(q.scheduledFor, q.cityId, q.pickup.copy(latitude = 34.031), q.destination))
        assertFalse(q.matchesPointRequest(q.scheduledFor, q.cityId, q.pickup, q.destination.copy(longitude = -5.011)))
    }

    @Test fun invalid_or_offset_free_requested_and_returned_times_are_not_reviewable() {
        val q = point()
        for (bad in listOf("", "PRIVATE-invalid", "2026-11-01T08:30:00", "2026-02-30T08:30:00Z")) {
            assertFalse(q.matchesPointRequest(bad, q.cityId, q.pickup, q.destination))
            assertFalse(q.copy(scheduledFor = bad).matchesPointRequest(q.scheduledFor, q.cityId, q.pickup, q.destination))
        }
    }

    @Test fun unknown_service_payment_and_conflicting_route_fields_cannot_become_point_reviews() {
        val q = point()
        for (bad in listOf(q.copy(serviceType = "FUTURE_PRIVATE"), q.copy(serviceType = "FIXED_ROUTE"),
            q.copy(fixedRouteDirectionVersionId = "direction"), q.copy(paymentMethod = "MANUAL_TRANSFER"),
            q.copy(paymentMethod = "FUTURE_PRIVATE"), q.copy(cityId = ""), q.copy(operatorId = ""))) {
            assertFalse(bad.matchesPointRequest(q.scheduledFor, q.cityId, q.pickup, q.destination))
        }
    }

    @Test fun invalid_points_are_not_matched_even_to_identical_invalid_responses() {
        val q = point()
        for (bad in listOf(Coordinates(Double.NaN, 0.0), Coordinates(0.0, Double.POSITIVE_INFINITY),
            Coordinates(91.0, 0.0), Coordinates(0.0, -181.0))) {
            assertFalse(q.copy(pickup = bad).matchesPointRequest(q.scheduledFor, q.cityId, bad, q.destination))
        }
    }

    @Test fun fixed_review_binds_the_immutable_direction_and_same_instant() {
        val q = point().copy(serviceType = "FIXED_ROUTE", fixedRouteDirectionVersionId = "direction-A")
        assertTrue(q.matchesFixedRouteRequest(q.scheduledFor, "direction-A"))
        assertTrue(q.matchesFixedRouteRequest("2026-11-01T09:30:00+01:00", "direction-A"))
        assertFalse(q.matchesFixedRouteRequest(q.scheduledFor, "direction-B"))
        assertFalse(q.matchesFixedRouteRequest("2026-11-02T08:30:00Z", "direction-A"))
        assertFalse(q.matchesFixedRouteRequest(q.scheduledFor, ""))
        assertFalse(q.copy(serviceType = "ON_DEMAND").matchesFixedRouteRequest(q.scheduledFor, "direction-A"))
        assertFalse(q.copy(paymentMethod = "UNKNOWN").matchesFixedRouteRequest(q.scheduledFor, "direction-A"))
    }
}
