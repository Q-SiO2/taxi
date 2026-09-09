package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

const val MANAGE_CITY_TARIFFS = "manage_city_tariffs"
const val MANAGE_OPERATOR_FEE_POLICIES = "manage_operator_fee_policies"
const val MANAGE_SCHEDULING_POLICY = "manage_scheduling_policy"

val PRICING_ECONOMICS_PERMISSIONS = setOf(
    MANAGE_CITY_TARIFFS,
    MANAGE_OPERATOR_FEE_POLICIES,
    MANAGE_SCHEDULING_POLICY,
)

@Serializable
data class PricingRuleRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    @SerialName("service_type") val serviceType: String,
    @SerialName("booking_type") val bookingType: String,
    @SerialName("fixed_route_direction_id") val fixedRouteDirectionId: String? = null,
    val name: String,
    val version: String,
    val model: String,
    @SerialName("fixed_amount") val fixedAmount: String? = null,
    val currency: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    val status: String,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    @SerialName("created_by_user_id") val createdByUserId: String? = null,
    @SerialName("submitted_by_user_id") val submittedByUserId: String? = null,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("activated_by_user_id") val activatedByUserId: String? = null,
    @SerialName("activated_at") val activatedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class PricingRuleCreateRequest(
    @SerialName("operator_id") val operatorId: String,
    val name: String,
    val version: String,
    @SerialName("fixed_amount") val fixedAmount: String,
    val currency: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("service_type") val serviceType: String = "ON_DEMAND",
    @SerialName("booking_type") val bookingType: String = "IMMEDIATE",
    @SerialName("fixed_route_direction_id") val fixedRouteDirectionId: String? = null,
    val model: String = "FIXED",
)

@Serializable
data class PricingRuleUpdateRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    val name: String,
    @SerialName("fixed_amount") val fixedAmount: String,
    val currency: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("clear_effective_until") val clearEffectiveUntil: Boolean = false,
)

@Serializable
data class OperatorFeePolicyRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    @SerialName("service_type") val serviceType: String,
    val version: String,
    val status: String,
    @SerialName("calculation_mode") val calculationMode: String,
    @SerialName("funding_mode") val fundingMode: String,
    @SerialName("eligible_base_code") val eligibleBaseCode: String,
    @SerialName("percentage_rate") val percentageRate: String? = null,
    @SerialName("flat_amount") val flatAmount: String? = null,
    val currency: String,
    @SerialName("rounding_rule") val roundingRule: String,
    @SerialName("minimum_driver_net") val minimumDriverNet: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    @SerialName("created_by_user_id") val createdByUserId: String? = null,
    @SerialName("submitted_by_user_id") val submittedByUserId: String? = null,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("activated_by_user_id") val activatedByUserId: String? = null,
    @SerialName("activated_at") val activatedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class OperatorFeePolicyCreateRequest(
    @SerialName("operator_id") val operatorId: String,
    val version: String,
    @SerialName("calculation_mode") val calculationMode: String,
    @SerialName("funding_mode") val fundingMode: String,
    @SerialName("percentage_rate") val percentageRate: String? = null,
    @SerialName("flat_amount") val flatAmount: String? = null,
    val currency: String,
    @SerialName("minimum_driver_net") val minimumDriverNet: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("service_type") val serviceType: String = "ON_DEMAND",
    @SerialName("eligible_base_code") val eligibleBaseCode: String = "TRANSPORT_FARE",
    @SerialName("rounding_rule") val roundingRule: String = "HALF_UP_0_01",
)

@Serializable
data class OperatorFeePolicyUpdateRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    @SerialName("calculation_mode") val calculationMode: String,
    @SerialName("funding_mode") val fundingMode: String,
    @SerialName("percentage_rate") val percentageRate: String? = null,
    @SerialName("flat_amount") val flatAmount: String? = null,
    val currency: String,
    @SerialName("minimum_driver_net") val minimumDriverNet: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("clear_effective_until") val clearEffectiveUntil: Boolean = false,
)

@Serializable
data class SchedulingPolicyRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    @SerialName("service_type") val serviceType: String,
    val version: String,
    val status: String,
    @SerialName("surcharge_amount") val surchargeAmount: String,
    val currency: String,
    val beneficiary: String,
    @SerialName("collection_timing_code") val collectionTimingCode: String,
    @SerialName("minimum_lead_minutes") val minimumLeadMinutes: Int,
    @SerialName("maximum_horizon_days") val maximumHorizonDays: Int,
    @SerialName("offer_open_minutes_before") val offerOpenMinutesBefore: Int,
    @SerialName("offer_response_seconds") val offerResponseSeconds: Int,
    @SerialName("commitment_deadline_minutes_before") val commitmentDeadlineMinutesBefore: Int,
    @SerialName("handoff_minutes_before") val handoffMinutesBefore: Int,
    @SerialName("protected_duration_minutes") val protectedDurationMinutes: Int,
    @SerialName("conflict_buffer_before_minutes") val conflictBufferBeforeMinutes: Int,
    @SerialName("conflict_buffer_after_minutes") val conflictBufferAfterMinutes: Int,
    @SerialName("passenger_cancel_cutoff_minutes") val passengerCancelCutoffMinutes: Int,
    @SerialName("driver_cancel_cutoff_minutes") val driverCancelCutoffMinutes: Int,
    @SerialName("surcharge_refund_mode") val surchargeRefundMode: String,
    @SerialName("fallback_matching_enabled") val fallbackMatchingEnabled: Boolean,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    @SerialName("created_by_user_id") val createdByUserId: String? = null,
    @SerialName("submitted_by_user_id") val submittedByUserId: String? = null,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("activated_by_user_id") val activatedByUserId: String? = null,
    @SerialName("activated_at") val activatedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class SchedulingPolicyCreateRequest(
    @SerialName("operator_id") val operatorId: String,
    val version: String,
    @SerialName("surcharge_amount") val surchargeAmount: String,
    val currency: String,
    val beneficiary: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("service_type") val serviceType: String = "ON_DEMAND",
    @SerialName("collection_timing_code") val collectionTimingCode: String = "AT_RIDE_SETTLEMENT",
    @SerialName("minimum_lead_minutes") val minimumLeadMinutes: Int = 60,
    @SerialName("maximum_horizon_days") val maximumHorizonDays: Int = 30,
    @SerialName("offer_open_minutes_before") val offerOpenMinutesBefore: Int = 1440,
    @SerialName("offer_response_seconds") val offerResponseSeconds: Int = 120,
    @SerialName("commitment_deadline_minutes_before") val commitmentDeadlineMinutesBefore: Int = 180,
    @SerialName("handoff_minutes_before") val handoffMinutesBefore: Int = 30,
    @SerialName("protected_duration_minutes") val protectedDurationMinutes: Int = 90,
    @SerialName("conflict_buffer_before_minutes") val conflictBufferBeforeMinutes: Int = 30,
    @SerialName("conflict_buffer_after_minutes") val conflictBufferAfterMinutes: Int = 30,
    @SerialName("passenger_cancel_cutoff_minutes") val passengerCancelCutoffMinutes: Int = 60,
    @SerialName("driver_cancel_cutoff_minutes") val driverCancelCutoffMinutes: Int = 120,
    @SerialName("surcharge_refund_mode") val surchargeRefundMode: String = "FULL_BEFORE_CUTOFF",
    @SerialName("fallback_matching_enabled") val fallbackMatchingEnabled: Boolean = true,
)

@Serializable
data class SchedulingPolicyUpdateRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    @SerialName("surcharge_amount") val surchargeAmount: String,
    val currency: String,
    val beneficiary: String,
    @SerialName("minimum_lead_minutes") val minimumLeadMinutes: Int,
    @SerialName("maximum_horizon_days") val maximumHorizonDays: Int,
    @SerialName("offer_open_minutes_before") val offerOpenMinutesBefore: Int,
    @SerialName("offer_response_seconds") val offerResponseSeconds: Int,
    @SerialName("commitment_deadline_minutes_before") val commitmentDeadlineMinutesBefore: Int,
    @SerialName("handoff_minutes_before") val handoffMinutesBefore: Int,
    @SerialName("protected_duration_minutes") val protectedDurationMinutes: Int,
    @SerialName("conflict_buffer_before_minutes") val conflictBufferBeforeMinutes: Int,
    @SerialName("conflict_buffer_after_minutes") val conflictBufferAfterMinutes: Int,
    @SerialName("passenger_cancel_cutoff_minutes") val passengerCancelCutoffMinutes: Int,
    @SerialName("driver_cancel_cutoff_minutes") val driverCancelCutoffMinutes: Int,
    @SerialName("surcharge_refund_mode") val surchargeRefundMode: String,
    @SerialName("fallback_matching_enabled") val fallbackMatchingEnabled: Boolean,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("clear_effective_until") val clearEffectiveUntil: Boolean = false,
)

@Serializable
data class PricingPolicyCommandRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    val reason: String,
)

data class PricingEconomicsSnapshot(
    val pricingRules: PagedResponse<PricingRuleRecord>? = null,
    val operatorFeePolicies: PagedResponse<OperatorFeePolicyRecord>? = null,
    val schedulingPolicies: PagedResponse<SchedulingPolicyRecord>? = null,
)

fun pricingPolicyTargetFor(status: String): String? = when (status) {
    "DRAFT" -> "IN_REVIEW"
    "IN_REVIEW" -> "ACTIVE"
    else -> null
}

private val versionPattern = Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
private val moneyPattern = Regex("^(0|[1-9][0-9]{0,9})(\\.[0-9]{1,2})?$")
private val percentagePattern = Regex("^(0|[1-9][0-9]?)(\\.[0-9]{1,4})?$")

fun validPolicyVersion(value: String): Boolean = versionPattern.matches(value.trim())

fun validMoney(value: String, allowZero: Boolean): Boolean {
    val normalized = value.trim()
    if (!moneyPattern.matches(normalized)) return false
    return allowZero || normalized.any { it in '1'..'9' }
}

fun validPercentage(value: String): Boolean {
    val normalized = value.trim()
    if (!percentagePattern.matches(normalized)) return false
    return (normalized.toDoubleOrNull() ?: return false) < 100.0
}

fun validCurrency(value: String): Boolean = value.trim().length == 3 && value.trim().all { it in 'A'..'Z' }

fun validZonedTimestamp(value: String): Boolean {
    val normalized = value.trim()
    if (!Regex("^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}(:\\d{2}(\\.\\d{1,6})?)?(Z|[+-]\\d{2}:\\d{2})$").matches(normalized)) {
        return false
    }
    return true
}
