package org.example.taximobile.operations.model

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

class AnalyticsModelsTest {
    private val json = Json { ignoreUnknownKeys = false }

    @Test
    fun suppressedFactRetainsScopeButNoMeasure() {
        val response = json.decodeFromString<OperationalMetricFactList>(
            """
            {
              "items": [{
                "bucket_start": "2026-08-29T12:00:00Z",
                "city_id": "11111111-1111-1111-1111-111111111111",
                "operator_id": null,
                "service_type": null,
                "booking_type": null,
                "fixed_route_direction_version_id": null,
                "pricing_rule_version_id": null,
                "operator_fee_policy_version_id": null,
                "scheduling_policy_version_id": null,
                "matching_algorithm_version": null,
                "metric_code": "DRIVER_APPLICATION_CREATED",
                "metric_family": "onboarding",
                "outcome_code": "NOT_STARTED",
                "category_code": null,
                "currency": null,
                "sample_count": null,
                "integer_value": null,
                "average_duration_seconds": null,
                "average_distance_meters": null,
                "amount_sum": null,
                "average_numeric_value": null,
                "average_per_entity": null,
                "minimum_per_entity": null,
                "maximum_per_entity": null,
                "distribution_gini": null,
                "suppressed": true,
                "source_watermark": "2026-08-29T12:10:00Z",
                "computed_at": "2026-08-29T12:11:00Z"
              }],
              "from_time": "2026-07-30T12:00:00Z",
              "to_time": "2026-08-29T12:00:00Z",
              "bucket": "HOUR",
              "definition_version": "operations-analytics-v1",
              "minimum_cell_size": 5,
              "late_event_policy": "RECOMPUTE_FROM_SOURCE_UNTIL_RETENTION",
              "retention_days": 730
            }
            """.trimIndent()
        )

        val fact = response.items.single()
        assertTrue(fact.suppressed)
        assertNull(fact.sampleCount)
        assertNull(fact.amountSum)
        assertNull(fact.distributionGini)
        assertEquals(5, response.minimumCellSize)
    }
}
