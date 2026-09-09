package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

const val VIEW_CONTROL_PLANE = "view_control_plane"
const val MANAGE_CITY_LIFECYCLE = "manage_city_lifecycle"

val PILOT_ENTRY_READINESS_GATES = listOf(
    "LEGAL_AND_OPERATOR_OWNERSHIP",
    "SERVICE_AREA_AND_TIMEZONE",
    "DRIVER_AND_VEHICLE_REQUIREMENTS",
    "TARIFF_AND_OPERATOR_FEE",
    "MATCHING_AND_CANCELLATION",
    "PAYMENT_AND_RECONCILIATION",
    "SUPPORT_SAFETY_AND_RETENTION",
    "LOCALIZATION_AR_FR_EN",
    "MAP_ROUTING_COVERAGE",
    "SECURITY_MONITORING_AND_ROLLBACK",
)
val PUBLIC_ACTIVATION_READINESS_GATES = PILOT_ENTRY_READINESS_GATES + "PILOT_SERVICE_AND_FAIRNESS"
const val POST_LAUNCH_REVIEW_GATE = "POST_LAUNCH_REVIEW"
const val MANAGE_SCOPED_STAFF_GRANTS = "manage_scoped_staff_grants"
const val VIEW_SCOPED_AUDIT = "view_scoped_audit"
const val REVIEW_DRIVER_APPLICATIONS = "review_driver_applications"
const val MANAGE_DRIVER_REQUIREMENTS = "manage_driver_requirements"
const val VIEW_SCOPED_OPERATIONAL_AGGREGATES = "view_scoped_operational_aggregates"

@Serializable
data class ScheduledBookingEconomicsRecord(
    @SerialName("transport_fare") val transportFare: String,
    @SerialName("scheduling_surcharge") val schedulingSurcharge: String,
    @SerialName("operator_service_fee") val operatorServiceFee: String,
    @SerialName("passenger_total") val passengerTotal: String,
    @SerialName("expected_driver_net") val expectedDriverNet: String,
    @SerialName("operator_allocation") val operatorAllocation: String,
    val currency: String,
    @SerialName("pricing_rule_version") val pricingRuleVersion: String,
    @SerialName("operator_fee_policy_version") val operatorFeePolicyVersion: String,
    @SerialName("scheduling_policy_version") val schedulingPolicyVersion: String,
)

@Serializable
data class ScheduledCancellationTermsRecord(
    @SerialName("passenger_cancel_cutoff_minutes") val passengerCancelCutoffMinutes: Int,
    @SerialName("surcharge_refund_mode") val surchargeRefundMode: String,
    val summary: String,
)

@Serializable
data class ScheduledCoordinateRecord(
    val latitude: Double,
    val longitude: Double,
    val address: String? = null,
)

@Serializable
data class ScheduledBookingExceptionRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    @SerialName("service_type") val serviceType: String,
    @SerialName("fixed_route_direction_version_id") val fixedRouteDirectionVersionId: String? = null,
    @SerialName("scheduled_for") val scheduledFor: String,
    @SerialName("city_timezone") val cityTimezone: String,
    val status: String,
    val pickup: ScheduledCoordinateRecord,
    val destination: ScheduledCoordinateRecord,
    val economics: ScheduledBookingEconomicsRecord,
    @SerialName("cancellation_terms") val cancellationTerms: ScheduledCancellationTermsRecord,
    @SerialName("driver_committed") val driverCommitted: Boolean,
    @SerialName("live_ride_id") val liveRideId: String? = null,
    @SerialName("cancellation_financial_outcome") val cancellationFinancialOutcome: String? = null,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class OperationsLoginRequest(
    val identifier: String,
    val password: String,
    @SerialName("device_label") val deviceLabel: String = "TaxiMobile operations web",
)

@Serializable
data class OperationsRefreshRequest(
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
data class OperationsTokenEnvelope(
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String? = null,
    @SerialName("csrf_token") val csrfToken: String? = null,
    @SerialName("token_type") val tokenType: String,
    @SerialName("expires_in") val expiresIn: Int,
    @SerialName("authentication_strength") val authenticationStrength: String = "PASSWORD_ONLY_LOCAL",
)

@Serializable
data class OperationsLoginEnvelope(
    @SerialName("access_token") val accessToken: String? = null,
    @SerialName("refresh_token") val refreshToken: String? = null,
    @SerialName("token_type") val tokenType: String? = null,
    @SerialName("expires_in") val expiresIn: Int,
    @SerialName("authentication_strength") val authenticationStrength: String? = null,
    @SerialName("csrf_token") val csrfToken: String? = null,
    @SerialName("challenge_id") val challengeId: String? = null,
    @SerialName("authentication_methods") val authenticationMethods: List<String> = emptyList(),
)

sealed interface OperationsLoginResult {
    data class Authenticated(val tokens: OperationsTokens) : OperationsLoginResult
    data class MfaRequired(
        val challengeId: String,
        val expiresIn: Int,
        val methods: List<String>,
    ) : OperationsLoginResult
}

fun OperationsLoginEnvelope.toLoginResult(): OperationsLoginResult = when {
    accessToken != null && tokenType != null && authenticationStrength != null ->
        OperationsLoginResult.Authenticated(
            OperationsTokens(
                accessToken,
                refreshToken,
                csrfToken,
                expiresIn,
                authenticationStrength,
            )
        )
    challengeId != null -> OperationsLoginResult.MfaRequired(
        challengeId = challengeId,
        expiresIn = expiresIn,
        methods = authenticationMethods,
    )
    else -> error("Login response contains neither a session nor an MFA challenge")
}

@Serializable
data class OperationsMfaVerificationRequest(
    @SerialName("challenge_id") val challengeId: String,
    val code: String,
)

@Serializable
data class OperationsMfaStepUpRequest(val code: String)

@Serializable
data class OperationsMfaStepUpResponse(
    @SerialName("verified_at") val verifiedAt: String,
    @SerialName("authentication_strength") val authenticationStrength: String,
)

/** Kept only in coordinator memory. It is never persisted to browser storage. */
data class OperationsTokens(
    val accessToken: String,
    val refreshToken: String?,
    val csrfToken: String?,
    val expiresIn: Int,
    val authenticationStrength: String,
)

fun OperationsTokenEnvelope.toInMemoryTokens() = OperationsTokens(
    accessToken = accessToken,
    refreshToken = refreshToken,
    csrfToken = csrfToken,
    expiresIn = expiresIn,
    authenticationStrength = authenticationStrength,
)

@Serializable
data class OperationsGrantSession(
    val id: String,
    @SerialName("role_template") val roleTemplate: String,
    @SerialName("market_id") val marketId: String? = null,
    @SerialName("operator_id") val operatorId: String? = null,
    @SerialName("city_id") val cityId: String? = null,
    val permissions: List<String>,
)

@Serializable
data class OperationsSession(
    @SerialName("user_id") val userId: String,
    @SerialName("session_id") val sessionId: String,
    val grants: List<OperationsGrantSession>,
    @SerialName("expires_at") val expiresAt: String? = null,
    @SerialName("mfa_verified_at") val mfaVerifiedAt: String? = null,
    @SerialName("authentication_strength") val authenticationStrength: String = "PASSWORD_ONLY_LOCAL",
) {
    val permissions: Set<String>
        get() = grants.flatMapTo(mutableSetOf()) { it.permissions }

    fun hasPermission(permission: String): Boolean = permission in permissions
}

@Serializable
data class PagedResponse<T>(
    val items: List<T>,
    val page: Int,
    val limit: Int,
    val total: Int,
)

@Serializable
data class LocalizedName(
    val en: String,
    val fr: String,
    val ar: String,
) {
    fun preferred(): String = en.ifBlank { fr.ifBlank { ar } }
}

@Serializable
data class Coordinate(
    val latitude: Double,
    val longitude: Double,
)

@Serializable
data class MarketRecord(
    val id: String,
    val code: String,
    val name: String,
    @SerialName("default_currency") val defaultCurrency: String,
    val status: String,
)

@Serializable
data class CityRecord(
    val id: String,
    @SerialName("market_id") val marketId: String,
    val code: String,
    @SerialName("localized_name") val localizedName: LocalizedName,
    val timezone: String,
    @SerialName("presentation_centroid") val presentationCentroid: Coordinate,
    @SerialName("lifecycle_status") val lifecycleStatus: String,
    @SerialName("active_configuration_version_id") val activeConfigurationVersionId: String? = null,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    @SerialName("is_legacy_compatibility") val isLegacyCompatibility: Boolean,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class OperatorRecord(
    val id: String,
    @SerialName("market_id") val marketId: String,
    @SerialName("cooperative_id") val cooperativeId: String? = null,
    val name: String,
    @SerialName("operator_type") val operatorType: String,
    val status: String,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class OperatorCityAssignment(
    val id: String,
    @SerialName("operator_id") val operatorId: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("service_type") val serviceType: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    val status: String,
    @SerialName("created_at") val createdAt: String,
    @SerialName("retired_at") val retiredAt: String? = null,
)

@Serializable
data class RolloutCitySummary(
    @SerialName("city_id") val cityId: String,
    val code: String,
    @SerialName("localized_name") val localizedName: LocalizedName,
    @SerialName("lifecycle_status") val lifecycleStatus: String,
    @SerialName("active_configuration_version_id") val activeConfigurationVersionId: String? = null,
    @SerialName("readiness_passed") val readinessPassed: Int,
    @SerialName("readiness_required") val readinessRequired: Int,
    @SerialName("missing_readiness_gates") val missingReadinessGates: List<String>,
    @SerialName("pilot_entry_passed") val pilotEntryPassed: Int,
    @SerialName("pilot_entry_required") val pilotEntryRequired: Int,
    @SerialName("missing_pilot_entry_gates") val missingPilotEntryGates: List<String>,
    @SerialName("public_activation_passed") val publicActivationPassed: Int,
    @SerialName("public_activation_required") val publicActivationRequired: Int,
    @SerialName("missing_public_activation_gates") val missingPublicActivationGates: List<String>,
    @SerialName("post_launch_review_status") val postLaunchReviewStatus: String,
)

@Serializable
data class RolloutOverview(
    @SerialName("visible_market_count") val visibleMarketCount: Int,
    @SerialName("visible_operator_count") val visibleOperatorCount: Int,
    @SerialName("visible_city_count") val visibleCityCount: Int,
    val cities: List<RolloutCitySummary>,
)

@Serializable
data class AdministrativeGrantRecord(
    val id: String,
    @SerialName("user_id") val userId: String,
    @SerialName("role_template") val roleTemplate: String,
    @SerialName("market_id") val marketId: String? = null,
    @SerialName("operator_id") val operatorId: String? = null,
    @SerialName("city_id") val cityId: String? = null,
    @SerialName("granted_by_user_id") val grantedByUserId: String,
    @SerialName("grant_reason") val grantReason: String,
    @SerialName("granted_at") val grantedAt: String,
    @SerialName("expires_at") val expiresAt: String? = null,
    @SerialName("revoked_at") val revokedAt: String? = null,
    @SerialName("revoked_by_user_id") val revokedByUserId: String? = null,
    @SerialName("revocation_reason") val revocationReason: String? = null,
)

@Serializable
data class AuditLogRecord(
    val id: String,
    @SerialName("actor_user_id") val actorUserId: String,
    val action: String,
    @SerialName("resource_type") val resourceType: String,
    @SerialName("resource_id") val resourceId: String,
    @SerialName("market_id") val marketId: String? = null,
    @SerialName("operator_id") val operatorId: String? = null,
    @SerialName("city_id") val cityId: String? = null,
    val changes: JsonObject,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class MultiPolygonGeometry(
    val type: String,
    val coordinates: List<List<List<List<Double>>>>,
)

@Serializable
data class ServiceAreaVersionRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    val version: String,
    val boundary: MultiPolygonGeometry,
    val status: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class ConfigurationServiceRecord(
    @SerialName("service_type") val serviceType: String,
    @SerialName("operator_city_assignment_id") val operatorCityAssignmentId: String,
    @SerialName("tariff_version_id") val tariffVersionId: String? = null,
    @SerialName("operator_fee_policy_version_id") val operatorFeePolicyVersionId: String? = null,
    @SerialName("scheduling_policy_version_id") val schedulingPolicyVersionId: String? = null,
    @SerialName("payment_capability_version_id") val paymentCapabilityVersionId: String? = null,
    val enabled: Boolean,
)

@Serializable
data class ConfigurationRouteRecord(
    @SerialName("fixed_route_version_id") val fixedRouteVersionId: String,
    @SerialName("immediate_booking_enabled") val immediateBookingEnabled: Boolean,
    @SerialName("scheduled_booking_enabled") val scheduledBookingEnabled: Boolean,
)

@Serializable
data class ReadinessCheckRecord(
    val id: String,
    @SerialName("gate_code") val gateCode: String,
    val status: String,
    @SerialName("non_secret_evidence_reference") val nonSecretEvidenceReference: String? = null,
    @SerialName("decided_at") val decidedAt: String? = null,
)

@Serializable
data class CityConfigurationRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    val version: String,
    val status: String,
    @SerialName("service_area_version_id") val serviceAreaVersionId: String,
    @SerialName("driver_requirement_version_id") val driverRequirementVersionId: String? = null,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    val services: List<ConfigurationServiceRecord>,
    val routes: List<ConfigurationRouteRecord> = emptyList(),
    @SerialName("readiness_checks") val readinessChecks: List<ReadinessCheckRecord>,
    @SerialName("missing_readiness_gates") val missingReadinessGates: List<String>,
    @SerialName("missing_pilot_entry_gates") val missingPilotEntryGates: List<String>,
    @SerialName("missing_public_activation_gates") val missingPublicActivationGates: List<String>,
    @SerialName("post_launch_review_status") val postLaunchReviewStatus: String,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("approved_at") val approvedAt: String? = null,
    @SerialName("activated_at") val activatedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class ReadinessDecisionRequest(
    @SerialName("gate_code") val gateCode: String,
    val status: String,
    @SerialName("non_secret_evidence_reference") val nonSecretEvidenceReference: String,
    @SerialName("expected_configuration_version") val expectedConfigurationVersion: Int,
)

@Serializable
data class CityLifecycleTransitionRequest(
    @SerialName("target_status") val targetStatus: String,
    @SerialName("expected_version") val expectedVersion: Int,
    val reason: String,
)

@Serializable
data class RecruitmentLocalizedCopy(
    val en: String,
    val fr: String,
    val ar: String,
)

@Serializable
data class DriverRequirementItemRecord(
    val id: String,
    @SerialName("requirement_code") val requirementCode: String,
    @SerialName("evidence_type") val evidenceType: String,
    @SerialName("allowed_evidence_types") val allowedEvidenceTypes: List<String>,
    val required: Boolean,
    @SerialName("validity_rule_code") val validityRuleCode: String,
    @SerialName("reference_type_code") val referenceTypeCode: String? = null,
    @SerialName("display_order") val displayOrder: Int,
    @SerialName("localized_copy_key") val localizedCopyKey: String,
    @SerialName("localized_label") val localizedLabel: RecruitmentLocalizedCopy,
    @SerialName("localized_description") val localizedDescription: RecruitmentLocalizedCopy,
)

@Serializable
data class DriverRequirementItemInput(
    @SerialName("requirement_code") val requirementCode: String,
    @SerialName("evidence_type") val evidenceType: String,
    val required: Boolean,
    @SerialName("validity_rule_code") val validityRuleCode: String,
    @SerialName("reference_type_code") val referenceTypeCode: String? = null,
    @SerialName("display_order") val displayOrder: Int,
    @SerialName("localized_copy_key") val localizedCopyKey: String,
    @SerialName("localized_label") val localizedLabel: RecruitmentLocalizedCopy,
    @SerialName("localized_description") val localizedDescription: RecruitmentLocalizedCopy,
)

@Serializable
data class DriverRequirementVersionRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    val version: String,
    val status: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    val items: List<DriverRequirementItemRecord>,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("activated_at") val activatedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class DriverRequirementVersionCreateRequest(
    val version: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    val items: List<DriverRequirementItemInput>,
)

@Serializable
data class DriverRequirementVersionUpdateRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    @SerialName("effective_from") val effectiveFrom: String? = null,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("clear_effective_until") val clearEffectiveUntil: Boolean = false,
    val items: List<DriverRequirementItemInput>? = null,
)

@Serializable
data class DriverRequirementVersionCommandRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    val reason: String,
)

@Serializable
data class OperationsDriverApplicationSummary(
    val id: String,
    @SerialName("driver_id") val driverId: String,
    @SerialName("display_name") val displayName: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("city_code") val cityCode: String,
    @SerialName("city_name") val cityName: LocalizedName,
    @SerialName("requirement_version_id") val requirementVersionId: String,
    @SerialName("requirement_version") val requirementVersion: String,
    val status: String,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class OperationsApplicationAnswer(
    @SerialName("requirement_item_id") val requirementItemId: String,
    @SerialName("answer_type") val answerType: String,
    @SerialName("boolean_value") val booleanValue: Boolean? = null,
    @SerialName("date_value") val dateValue: String? = null,
    @SerialName("text_value") val textValue: String? = null,
)

@Serializable
data class OperationsApplicationEvidence(
    @SerialName("requirement_item_id") val requirementItemId: String,
    @SerialName("evidence_type") val evidenceType: String,
    @SerialName("profile_id") val profileId: String? = null,
    @SerialName("vehicle_id") val vehicleId: String? = null,
    @SerialName("credential_id") val credentialId: String? = null,
    @SerialName("document_id") val documentId: String? = null,
    val status: String,
)

@Serializable
data class OperationsApplicationDocument(
    val id: String,
    @SerialName("requirement_item_id") val requirementItemId: String,
    @SerialName("media_type") val mediaType: String,
    @SerialName("byte_size") val byteSize: Long,
    @SerialName("scan_status") val scanStatus: String,
    @SerialName("uploaded_at") val uploadedAt: String,
    @SerialName("deleted_at") val deletedAt: String? = null,
)

@Serializable
data class OperationsApplicantSafeDecision(
    val decision: String,
    @SerialName("reason_code") val reasonCode: String,
    val message: String,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class OperationsCityAuthorization(
    val id: String,
    @SerialName("city_id") val cityId: String,
    val status: String,
    @SerialName("vehicle_id") val vehicleId: String? = null,
    @SerialName("service_types") val serviceTypes: List<String>,
    @SerialName("scheduled_offers_enabled") val scheduledOffersEnabled: Boolean,
    @SerialName("valid_from") val validFrom: String,
    @SerialName("valid_until") val validUntil: String? = null,
)

@Serializable
data class OperationsCityApplicationRecord(
    val id: String,
    @SerialName("driver_id") val driverId: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("city_code") val cityCode: String,
    @SerialName("city_name") val cityName: LocalizedName,
    @SerialName("requirement_version_id") val requirementVersionId: String,
    @SerialName("requirement_version") val requirementVersion: String,
    val status: String,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    @SerialName("submission_revision") val submissionRevision: Int,
    val editable: Boolean,
    val complete: Boolean,
    @SerialName("missing_required_item_ids") val missingRequiredItemIds: List<String>,
    @SerialName("document_upload_available") val documentUploadAvailable: Boolean,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("reviewed_at") val reviewedAt: String? = null,
    @SerialName("withdrawn_at") val withdrawnAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
    val requirements: List<DriverRequirementItemRecord>,
    val answers: List<OperationsApplicationAnswer>,
    val evidence: List<OperationsApplicationEvidence>,
    val documents: List<OperationsApplicationDocument>,
    @SerialName("latest_decision") val latestDecision: OperationsApplicantSafeDecision? = null,
    val authorization: OperationsCityAuthorization? = null,
)

@Serializable
data class OperationsDecisionRecord(
    val id: String,
    @SerialName("reviewer_user_id") val reviewerUserId: String,
    val decision: String,
    @SerialName("reason_code") val reasonCode: String,
    @SerialName("applicant_safe_message") val applicantSafeMessage: String,
    @SerialName("application_version") val applicationVersion: Int,
    @SerialName("submission_revision") val submissionRevision: Int,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class OperationsDriverApplicationDetail(
    val application: OperationsCityApplicationRecord,
    @SerialName("applicant_display_name") val applicantDisplayName: String,
    @SerialName("applicant_phone_number") val applicantPhoneNumber: String? = null,
    @SerialName("applicant_email") val applicantEmail: String? = null,
    val decisions: List<OperationsDecisionRecord>,
)

@Serializable
data class DriverApplicationDecisionRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    val decision: String,
    @SerialName("reason_code") val reasonCode: String,
    @SerialName("applicant_safe_message") val applicantSafeMessage: String,
    @SerialName("authorized_service_types") val authorizedServiceTypes: List<String>? = null,
    @SerialName("authorized_vehicle_id") val authorizedVehicleId: String? = null,
    @SerialName("authorization_valid_until") val authorizationValidUntil: String? = null,
)

@Serializable
data class SuppressedAggregateCountRecord(
    val status: String,
    val value: Int? = null,
    val suppressed: Boolean,
)

@Serializable
data class DriverOnboardingAggregateRecord(
    @SerialName("city_id") val cityId: String,
    @SerialName("as_of") val asOf: String,
    @SerialName("minimum_cell_size") val minimumCellSize: Int,
    @SerialName("total_applications") val totalApplications: Int? = null,
    @SerialName("total_suppressed") val totalSuppressed: Boolean,
    @SerialName("status_counts") val statusCounts: List<SuppressedAggregateCountRecord>,
    @SerialName("decided_application_count") val decidedApplicationCount: Int? = null,
    @SerialName("average_review_seconds") val averageReviewSeconds: Double? = null,
    @SerialName("review_duration_suppressed") val reviewDurationSuppressed: Boolean,
)

@Serializable
data class LogoutResponse(val success: Boolean)

data class OperationsScope(
    val marketId: String? = null,
    val operatorId: String? = null,
    val cityId: String? = null,
)

data class OperationsSnapshot(
    val markets: PagedResponse<MarketRecord>,
    val cities: PagedResponse<CityRecord>,
    val operators: PagedResponse<OperatorRecord>,
    val assignments: PagedResponse<OperatorCityAssignment>,
    val rollout: RolloutOverview,
    val grants: PagedResponse<AdministrativeGrantRecord>? = null,
    val grantRequests: PagedResponse<AdministrativeGrantChangeRequestRecord>? = null,
    val auditLogs: PagedResponse<AuditLogRecord>? = null,
    val serviceAreas: PagedResponse<ServiceAreaVersionRecord>? = null,
    val configurations: PagedResponse<CityConfigurationRecord>? = null,
    val driverRequirementVersions: PagedResponse<DriverRequirementVersionRecord>? = null,
    val driverApplications: PagedResponse<OperationsDriverApplicationSummary>? = null,
    val onboardingAggregate: DriverOnboardingAggregateRecord? = null,
    val pricingEconomics: PricingEconomicsSnapshot? = null,
    val fixedRoutes: PagedResponse<FixedRouteRecord>? = null,
    val fixedRouteFareOptions: List<FixedRouteFareOptionRecord> = emptyList(),
    val scheduledBookingExceptions: PagedResponse<ScheduledBookingExceptionRecord>? = null,
    val analytics: OperationsAnalyticsSnapshot? = null,
    val caseOperations: CaseOperationsSnapshot? = null,
    val paymentOperations: PaymentOperationsSnapshot? = null,
    val securityIncidents: SecurityIncidentWorkspace? = null,
)

enum class OperationsDestination(val title: String, val supportingText: String) {
    ROLLOUT("Rollout overview", "National readiness and city status"),
    CITIES("Cities", "Lifecycle and coherent configuration"),
    OPERATORS("Operators", "Service authority and assignments"),
    STAFF("Staff access", "Scoped administrative grants"),
    DRIVER_RECRUITMENT("Driver recruitment", "City requirements, scoped review, and funnel health"),
    PRICING_ECONOMICS("Pricing & economics", "Tariffs, transparent operator fees, and scheduling surcharges"),
    PAYMENTS("Payments", "City capabilities, recipients, transfer reconciliation, and refunds"),
    FIXED_ROUTES("Fixed routes", "Directions, stops, geometry, fare links, and publication"),
    SCHEDULED_EXCEPTIONS("Scheduled exceptions", "Unfulfilled, cancelling, offering, and handoff review"),
    ANALYTICS("Rollout intelligence", "Privacy-bounded service, finance, supply, and fairness facts"),
    CASE_OPERATIONS("Support & safety", "Scoped queues, overdue alerts, assignment, and response"),
    ACCOUNT_SECURITY("Account security", "Case-linked session revocation, suspension, and recovery"),
    SECURITY_INCIDENTS("Security incidents", "Containment timeline, recovery, and postmortem control"),
    AUDIT("Audit", "Append-oriented scoped activity"),
}

fun availableDestinations(permissions: Set<String>): List<OperationsDestination> = buildList {
    if (VIEW_CONTROL_PLANE in permissions) {
        add(OperationsDestination.ROLLOUT)
        add(OperationsDestination.CITIES)
        add(OperationsDestination.OPERATORS)
    }
    if (MANAGE_SCOPED_STAFF_GRANTS in permissions) add(OperationsDestination.STAFF)
    if (
        REVIEW_DRIVER_APPLICATIONS in permissions ||
        MANAGE_DRIVER_REQUIREMENTS in permissions ||
        VIEW_SCOPED_OPERATIONAL_AGGREGATES in permissions
    ) add(OperationsDestination.DRIVER_RECRUITMENT)
    if (permissions.any { it in PRICING_ECONOMICS_PERMISSIONS }) {
        add(OperationsDestination.PRICING_ECONOMICS)
    }
    if (MANAGE_PAYMENT_CAPABILITIES in permissions || RECONCILE_PAYMENTS in permissions) {
        add(OperationsDestination.PAYMENTS)
    }
    if (MANAGE_FIXED_ROUTES in permissions) add(OperationsDestination.FIXED_ROUTES)
    if (MANAGE_SCHEDULING_POLICY in permissions) add(OperationsDestination.SCHEDULED_EXCEPTIONS)
    if (VIEW_SCOPED_OPERATIONAL_AGGREGATES in permissions) add(OperationsDestination.ANALYTICS)
    if (MANAGE_SUPPORT_CASES in permissions || MANAGE_SAFETY_CASES in permissions) {
        add(OperationsDestination.CASE_OPERATIONS)
    }
    if (MANAGE_ACCOUNT_SECURITY in permissions) add(OperationsDestination.ACCOUNT_SECURITY)
    if (MANAGE_SECURITY_INCIDENTS in permissions) add(OperationsDestination.SECURITY_INCIDENTS)
    if (VIEW_SCOPED_AUDIT in permissions) add(OperationsDestination.AUDIT)
}

fun lifecycleTargetsFor(status: String): List<String> = when (status) {
    "DRAFT" -> listOf("CONFIGURING")
    "CONFIGURING" -> listOf("PILOT")
    "PILOT" -> listOf("ACTIVE")
    "ACTIVE" -> listOf("PAUSED", "RETIRED")
    "PAUSED" -> listOf("ACTIVE", "RETIRED")
    else -> emptyList()
}

fun OperationsSnapshot.normalizedScope(requested: OperationsScope): OperationsScope {
    val marketId = requested.marketId?.takeIf { id -> markets.items.any { it.id == id } }
        ?: markets.items.firstOrNull()?.id
    val operatorId = requested.operatorId?.takeIf { id ->
        operators.items.any { it.id == id && (marketId == null || it.marketId == marketId) }
    }
    val cityId = requested.cityId?.takeIf { id ->
        cities.items.any { it.id == id && (marketId == null || it.marketId == marketId) }
    }
    return OperationsScope(marketId = marketId, operatorId = operatorId, cityId = cityId)
}
