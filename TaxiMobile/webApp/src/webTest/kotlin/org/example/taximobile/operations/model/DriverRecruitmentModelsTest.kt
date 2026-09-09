package org.example.taximobile.operations.model

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

class DriverRecruitmentModelsTest {
    @Test
    fun `suppressed aggregate cells remain absent rather than becoming zero`() {
        val aggregate = Json { ignoreUnknownKeys = true }.decodeFromString<DriverOnboardingAggregateRecord>(
            """{
              "city_id":"city",
              "as_of":"2026-08-24T12:00:00Z",
              "minimum_cell_size":5,
              "total_applications":null,
              "total_suppressed":true,
              "status_counts":[{"status":"APPROVED","value":null,"suppressed":true}],
              "decided_application_count":null,
              "average_review_seconds":null,
              "review_duration_suppressed":true
            }""",
        )

        assertTrue(aggregate.totalSuppressed)
        assertNull(aggregate.totalApplications)
        assertTrue(aggregate.statusCounts.single().suppressed)
        assertNull(aggregate.statusCounts.single().value)
    }

    @Test
    fun `review permission exposes only the recruitment destination addition`() {
        val destinations = availableDestinations(setOf(VIEW_CONTROL_PLANE, REVIEW_DRIVER_APPLICATIONS))

        assertEquals(OperationsDestination.DRIVER_RECRUITMENT, destinations.last())
        assertTrue(OperationsDestination.STAFF !in destinations)
        assertTrue(OperationsDestination.AUDIT !in destinations)
    }
}
