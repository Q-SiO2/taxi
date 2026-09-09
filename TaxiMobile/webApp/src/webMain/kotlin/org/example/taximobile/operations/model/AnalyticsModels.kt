package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class AnalyticsMetricDefinition(
    val code: String,
    val family: String,
    val title: String,
    val unit: String,
    val source: String,
    val purpose: String,
    val owner: String,
    @SerialName("definition_version") val definitionVersion: String,
    @SerialName("retention_days") val retentionDays: Int,
    @SerialName("late_event_policy") val lateEventPolicy: String,
    @SerialName("minimum_cell_size") val minimumCellSize: Int,
)

@Serializable
data class AnalyticsMetricDefinitionList(
    val items: List<AnalyticsMetricDefinition>,
)

@Serializable
data class OperationalMetricFact(
    @SerialName("bucket_start") val bucketStart: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String? = null,
    @SerialName("service_type") val serviceType: String? = null,
    @SerialName("booking_type") val bookingType: String? = null,
    @SerialName("fixed_route_direction_version_id") val fixedRouteDirectionVersionId: String? = null,
    @SerialName("pricing_rule_version_id") val pricingRuleVersionId: String? = null,
    @SerialName("operator_fee_policy_version_id") val operatorFeePolicyVersionId: String? = null,
    @SerialName("scheduling_policy_version_id") val schedulingPolicyVersionId: String? = null,
    @SerialName("matching_algorithm_version") val matchingAlgorithmVersion: String? = null,
    @SerialName("metric_code") val metricCode: String,
    @SerialName("metric_family") val metricFamily: String,
    @SerialName("outcome_code") val outcomeCode: String? = null,
    @SerialName("category_code") val categoryCode: String? = null,
    val currency: String? = null,
    @SerialName("sample_count") val sampleCount: Long? = null,
    @SerialName("integer_value") val integerValue: Long? = null,
    @SerialName("average_duration_seconds") val averageDurationSeconds: String? = null,
    @SerialName("average_distance_meters") val averageDistanceMeters: String? = null,
    @SerialName("amount_sum") val amountSum: String? = null,
    @SerialName("average_numeric_value") val averageNumericValue: String? = null,
    @SerialName("average_per_entity") val averagePerEntity: String? = null,
    @SerialName("minimum_per_entity") val minimumPerEntity: Long? = null,
    @SerialName("maximum_per_entity") val maximumPerEntity: Long? = null,
    @SerialName("distribution_gini") val distributionGini: String? = null,
    val suppressed: Boolean,
    @SerialName("source_watermark") val sourceWatermark: String,
    @SerialName("computed_at") val computedAt: String,
)

@Serializable
data class OperationalMetricFactList(
    val items: List<OperationalMetricFact>,
    @SerialName("from_time") val fromTime: String,
    @SerialName("to_time") val toTime: String,
    val bucket: String,
    @SerialName("definition_version") val definitionVersion: String,
    @SerialName("minimum_cell_size") val minimumCellSize: Int,
    @SerialName("late_event_policy") val lateEventPolicy: String,
    @SerialName("retention_days") val retentionDays: Int,
)

data class OperationsAnalyticsSnapshot(
    val definitions: List<AnalyticsMetricDefinition>,
    val facts: OperationalMetricFactList,
)
