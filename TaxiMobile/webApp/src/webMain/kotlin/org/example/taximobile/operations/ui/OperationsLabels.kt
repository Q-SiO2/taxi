package org.example.taximobile.operations.ui

import org.example.taximobile.operations.model.OperationsDestination
import org.example.taximobile.operations.model.RecruitmentLocalizedCopy
import androidx.compose.runtime.Composable
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.TextDirection
import org.example.taximobile.feature.ui.text.hasArabicScript
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.example.taximobile.feature.ui.theme.taxiArabicFontFamily
import org.jetbrains.compose.resources.StringResource
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

internal fun OperationsDestination.titleResource(): StringResource = when (this) {
    OperationsDestination.ROLLOUT -> Res.string.web_nav_rollout
    OperationsDestination.CITIES -> Res.string.web_nav_cities
    OperationsDestination.OPERATORS -> Res.string.web_nav_operators
    OperationsDestination.STAFF -> Res.string.web_nav_staff
    OperationsDestination.DRIVER_RECRUITMENT -> Res.string.web_nav_driver_recruitment
    OperationsDestination.PRICING_ECONOMICS -> Res.string.web_nav_pricing_economics
    OperationsDestination.PAYMENTS -> Res.string.web_nav_payments
    OperationsDestination.FIXED_ROUTES -> Res.string.web_nav_fixed_routes
    OperationsDestination.SCHEDULED_EXCEPTIONS -> Res.string.web_nav_scheduled_exceptions
    OperationsDestination.ANALYTICS -> Res.string.web_nav_analytics
    OperationsDestination.CASE_OPERATIONS -> Res.string.web_nav_case_operations
    OperationsDestination.ACCOUNT_SECURITY -> Res.string.web_nav_account_security
    OperationsDestination.SECURITY_INCIDENTS -> Res.string.web_nav_security_incidents
    OperationsDestination.AUDIT -> Res.string.web_nav_audit
}

/** Labels never replace wire values or determine status tone/available commands. */
internal fun recruitmentCodeResource(code: String): StringResource? = when (code) {
    "DRAFT" -> Res.string.web_recruit_draft
    "REPLACED" -> Res.string.web_recruit_replaced
    "IN_REVIEW" -> Res.string.verification_under_review
    "ACTIVE" -> Res.string.account_status_active
    "MISSING" -> Res.string.web_recruit_missing
    "PRESENT" -> Res.string.web_recruit_present
    "PENDING" -> Res.string.web_recruit_pending
    "ACCEPTED" -> Res.string.web_recruit_accepted
    "QUARANTINED" -> Res.string.web_recruit_quarantined
    "CLEAN" -> Res.string.web_recruit_clean
    "ERROR" -> Res.string.web_recruit_scan_error
    "REVOKED" -> Res.string.web_recruit_revoked
    "VALID" -> Res.string.web_recruit_valid
    "VERIFIED" -> Res.string.vehicle_verification_verified
    "UNVERIFIED" -> Res.string.web_recruit_unverified
    "ON_DEMAND" -> Res.string.service_type_on_demand
    "FIXED_ROUTE" -> Res.string.service_type_fixed_route
    "SCHEDULED" -> Res.string.service_type_scheduled
    "PROFILE" -> Res.string.web_evidence_profile
    "VEHICLE" -> Res.string.web_evidence_vehicle
    "CREDENTIAL" -> Res.string.web_evidence_credential
    "DOCUMENT" -> Res.string.web_evidence_document
    "BOOLEAN" -> Res.string.web_evidence_boolean
    "DATE" -> Res.string.web_evidence_date
    "TEXT" -> Res.string.web_evidence_text
    "PROFILE_OWNED" -> Res.string.web_rule_owned
    "VEHICLE_OWNED" -> Res.string.web_rule_owned
    "CREDENTIAL_OWNED" -> Res.string.web_rule_owned
    "VEHICLE_VERIFIED" -> Res.string.web_rule_verified
    "CREDENTIAL_VERIFIED" -> Res.string.web_rule_verified
    "CREDENTIAL_UNEXPIRED" -> Res.string.web_rule_unexpired
    "DOCUMENT_SCANNED_CLEAN" -> Res.string.web_rule_clean
    "BOOLEAN_TRUE" -> Res.string.web_rule_true
    "DATE_NOT_FUTURE" -> Res.string.web_rule_date
    "TEXT_PRESENT" -> Res.string.web_rule_text
    "START_REVIEW" -> Res.string.web_decision_start
    "REQUEST_ADDITIONAL_INFORMATION" -> Res.string.web_decision_more
    "APPROVE" -> Res.string.web_decision_approve
    "REJECT" -> Res.string.web_decision_reject
    "MANUAL_REVIEW_STARTED" -> Res.string.web_reason_started
    "MISSING_OR_INVALID_EVIDENCE" -> Res.string.web_reason_evidence
    "CREDENTIAL_NOT_VALID" -> Res.string.web_reason_credential
    "VEHICLE_NOT_ELIGIBLE" -> Res.string.web_reason_vehicle
    "JURISDICTION_REQUIREMENT_NOT_MET" -> Res.string.web_reason_jurisdiction
    "REQUIREMENTS_CONFIRMED" -> Res.string.web_reason_confirmed
    "LEGACY_COMPATIBILITY_APPROVAL" -> Res.string.web_reason_legacy
    "DUPLICATE_APPLICATION" -> Res.string.web_reason_duplicate
    "SAFETY_REVIEW" -> Res.string.web_reason_safety
    "ELIGIBILITY_REVIEW" -> Res.string.web_reason_eligibility
    "OPERATING_PERMISSION_WITHDRAWN" -> Res.string.web_reason_withdrawn
    "ELIGIBILITY_REVIEW_PASSED" -> Res.string.web_reason_passed
    "SUSPEND" -> Res.string.web_auth_suspend
    "REVOKE" -> Res.string.web_auth_revoke
    "REINSTATE" -> Res.string.web_auth_reinstate
    "NOT_STARTED", "SUBMITTED", "UNDER_REVIEW", "ADDITIONAL_INFORMATION_REQUIRED",
    "APPROVED", "REJECTED", "WITHDRAWN", "SUSPENDED", "EXPIRED" ->
        org.example.taximobile.feature.app.driverApplicationStatusResource(code)
    else -> null
}

@Composable
internal fun recruitmentLabel(code: String): String = recruitmentCodeResource(code)?.let {
    stringResource(it)
} ?: stringResource(Res.string.web_recruit_unknown_code, ltrIsolate(code))

internal fun RecruitmentLocalizedCopy.inLanguage(language: String): String =
    when (language.lowercase().substringBefore('-').substringBefore('_')) {
        "ar" -> ar.ifBlank { fr.ifBlank { en } }
        "fr" -> fr.ifBlank { en.ifBlank { ar } }
        else -> en.ifBlank { fr.ifBlank { ar } }
    }

@Composable
internal fun recruitmentTextStyle(value: String): TextStyle =
    MaterialTheme.typography.bodyLarge.copy(
        fontFamily = if (hasArabicScript(value)) taxiArabicFontFamily()
        else MaterialTheme.typography.bodyLarge.fontFamily,
        textDirection = TextDirection.Content,
    )

/** Read-only readiness labels; gate codes and recorded outcomes remain authoritative. */
internal fun rolloutCodeResource(code: String): StringResource? = when (code) {
    "DRAFT", "ACTIVE", "PENDING" -> recruitmentCodeResource(code)
    "CONFIGURING" -> Res.string.web_city_configuring
    "PILOT" -> Res.string.web_city_pilot
    "PAUSED" -> Res.string.web_city_paused
    "RETIRED" -> Res.string.web_city_retired
    "PASSED" -> Res.string.web_check_passed
    "FAILED" -> Res.string.web_check_failed
    "LEGAL_AND_OPERATOR_OWNERSHIP" -> Res.string.web_gate_legal
    "SERVICE_AREA_AND_TIMEZONE" -> Res.string.web_gate_area
    "DRIVER_AND_VEHICLE_REQUIREMENTS" -> Res.string.web_gate_requirements
    "TARIFF_AND_OPERATOR_FEE" -> Res.string.web_gate_fares
    "MATCHING_AND_CANCELLATION" -> Res.string.web_gate_matching
    "PAYMENT_AND_RECONCILIATION" -> Res.string.web_gate_payments
    "SUPPORT_SAFETY_AND_RETENTION" -> Res.string.web_gate_support
    "LOCALIZATION_AR_FR_EN" -> Res.string.web_gate_languages
    "MAP_ROUTING_COVERAGE" -> Res.string.web_gate_maps
    "SECURITY_MONITORING_AND_ROLLBACK" -> Res.string.web_gate_security
    "PILOT_SERVICE_AND_FAIRNESS" -> Res.string.web_gate_pilot
    "POST_LAUNCH_REVIEW" -> Res.string.web_gate_post_launch
    else -> null
}

@Composable
internal fun rolloutLabel(code: String): String = rolloutCodeResource(code)?.let {
    stringResource(it)
} ?: stringResource(Res.string.web_recruit_unknown_code, ltrIsolate(code))

/** Payment presentation only: never changes wire statuses or allowed commands. */
internal fun paymentCodeResource(code: String): StringResource? = when (code) {
    "CASH" -> Res.string.payment_method_cash
    "MANUAL_TRANSFER" -> Res.string.payment_method_manual_transfer
    "EXTERNAL_TRANSFER" -> Res.string.web_pay_external_transfer
    "PENDING" -> Res.string.payment_status_pending
    "PROCESSING" -> Res.string.payment_status_processing
    "COMPLETED" -> Res.string.payment_status_completed
    "FAILED" -> Res.string.payment_status_failed
    "CANCELLED" -> Res.string.payment_status_cancelled
    "DISPUTED" -> Res.string.payment_status_disputed
    "REFUNDED" -> Res.string.payment_status_refunded
    "RETIRED" -> Res.string.web_city_retired
    "DRAFT", "IN_REVIEW", "APPROVED", "ACTIVE", "VERIFIED" -> recruitmentCodeResource(code)
    "submit" -> Res.string.web_req_submit_review
    "approve" -> Res.string.web_decision_approve
    "activate" -> Res.string.web_pay_activate
    else -> null
}

@Composable
internal fun paymentLabel(code: String): String = paymentCodeResource(code)?.let {
    stringResource(it)
} ?: stringResource(Res.string.web_recruit_unknown_code, ltrIsolate(code))

/** Case labels are display-only; note visibility, permissions and transitions use wire codes. */
internal fun caseCodeResource(code: String): StringResource? = when (code) {
    "SUPPORT" -> Res.string.web_case_support
    "SAFETY" -> Res.string.web_case_safety
    "OPEN" -> Res.string.support_status_open
    "IN_PROGRESS" -> Res.string.support_status_in_progress
    "RESOLVED" -> Res.string.support_status_resolved
    "CLOSED" -> Res.string.support_status_closed
    "SUBMITTED" -> Res.string.safety_status_submitted
    "ACKNOWLEDGED" -> Res.string.safety_status_acknowledged
    "ESCALATED" -> Res.string.safety_status_escalated
    "LOW" -> Res.string.web_case_low
    "NORMAL" -> Res.string.web_case_normal
    "HIGH" -> Res.string.web_case_high
    "URGENT" -> Res.string.web_case_urgent
    "INTERNAL" -> Res.string.web_case_internal
    "PARTICIPANT" -> Res.string.web_case_participant
    "RIDE_PROBLEM" -> Res.string.support_category_ride_problem
    "FARE_DISPUTE" -> Res.string.support_category_fare_dispute
    "ACCOUNT_ACCESS" -> Res.string.support_category_account_access
    "OTHER" -> Res.string.support_category_other
    "IMMEDIATE_DANGER" -> Res.string.safety_category_immediate_danger
    "HARASSMENT" -> Res.string.safety_category_harassment
    "ASSAULT" -> Res.string.safety_category_assault
    "UNSAFE_DRIVING" -> Res.string.safety_category_unsafe_driving
    "DISCRIMINATION" -> Res.string.safety_category_discrimination
    "VEHICLE_SAFETY" -> Res.string.safety_category_vehicle_safety
    "OTHER_SAFETY" -> Res.string.safety_category_other
    "INFORMATION_PROVIDED" -> Res.string.web_case_information
    "ACTION_TAKEN" -> Res.string.web_case_action_taken
    "REFUND_RECORDED" -> Res.string.web_case_refund_recorded
    "DUPLICATE" -> Res.string.web_case_duplicate
    "OUT_OF_SCOPE" -> Res.string.web_case_out_of_scope
    "NO_ACTION" -> Res.string.web_case_no_action
    "SAFETY_ACTION_TAKEN" -> Res.string.web_case_safety_action
    "REFERRED_TO_AUTHORITIES" -> Res.string.web_case_authorities
    "NO_PLATFORM_ACTION" -> Res.string.web_case_no_platform_action
    "LITIGATION" -> Res.string.web_case_litigation
    "REGULATORY_REQUEST" -> Res.string.web_case_regulatory
    "LAW_ENFORCEMENT_REQUEST" -> Res.string.web_case_law_enforcement
    "DISPUTE_PRESERVATION" -> Res.string.web_case_dispute_preservation
    "OTHER_LEGAL_OBLIGATION" -> Res.string.web_case_other_obligation
    "OBLIGATION_ENDED" -> Res.string.web_case_obligation_ended
    "REQUEST_WITHDRAWN" -> Res.string.web_case_request_withdrawn
    "SUPERSEDED" -> Res.string.web_case_superseded
    "PLACED_IN_ERROR" -> Res.string.web_case_placed_in_error
    "ACTIVE" -> Res.string.account_status_active
    "RELEASED" -> Res.string.web_case_released
    "ERASED", "PERSONAL_DATA_ERASED" -> Res.string.web_case_erased
    else -> null
}

@Composable
internal fun caseLabel(code: String): String = caseCodeResource(code)?.let {
    stringResource(it)
} ?: stringResource(Res.string.web_recruit_unknown_code, ltrIsolate(code))

internal fun bookingCodeResource(code: String): StringResource? = when (code) {
    "SCHEDULED" -> Res.string.web_booking_scheduled
    "OFFERING" -> Res.string.web_booking_offering
    "DRIVER_COMMITTED" -> Res.string.web_booking_driver_committed
    "DISPATCH_HANDOFF" -> Res.string.web_booking_handoff
    "LIVE_RIDE_CREATED" -> Res.string.web_booking_live_created
    "UNFULFILLED" -> Res.string.web_booking_unfulfilled
    "CANCELLED" -> Res.string.payment_status_cancelled
    "NO_CHARGE" -> Res.string.web_booking_no_charge
    "SURCHARGE_RETAINED" -> Res.string.web_booking_surcharge_retained
    "REFUND_PENDING" -> Res.string.web_booking_refund_pending
    "REFUNDED" -> Res.string.payment_status_refunded
    else -> null
}

/** Only known policy codes have display terms; unknown codes never imply no refund. */
internal fun bookingRefundCodeResource(code: String): StringResource? = when (code) {
    "ALWAYS_FULL" -> Res.string.scheduled_refund_always_full
    "FULL_BEFORE_CUTOFF" -> Res.string.web_booking_refund_before
    "NON_REFUNDABLE" -> Res.string.scheduled_refund_never
    else -> null
}

@Composable
internal fun bookingLabel(code: String): String = bookingCodeResource(code)?.let {
    stringResource(it)
} ?: stringResource(Res.string.web_recruit_unknown_code, ltrIsolate(code))

