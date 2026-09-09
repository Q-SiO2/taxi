package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

const val MANAGE_PAYMENT_CAPABILITIES = "manage_payment_capabilities"
const val RECONCILE_PAYMENTS = "reconcile_payments"

@Serializable
data class PaymentRecipientRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    val label: String,
    @SerialName("recipient_name") val recipientName: String,
    @SerialName("bank_account") val bankAccount: String? = null,
    @SerialName("wallet_id") val walletId: String? = null,
    val status: String,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    @SerialName("verified_at") val verifiedAt: String? = null,
    @SerialName("retired_at") val retiredAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class PaymentRecipientCreateRequest(
    @SerialName("operator_id") val operatorId: String,
    val label: String,
    @SerialName("recipient_name") val recipientName: String,
    @SerialName("bank_account") val bankAccount: String? = null,
    @SerialName("wallet_id") val walletId: String? = null,
)

@Serializable
data class PaymentRecipientCommandRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    val reason: String,
)

@Serializable
data class PaymentCapabilityRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    @SerialName("service_type") val serviceType: String,
    val version: String,
    val status: String,
    @SerialName("cash_enabled") val cashEnabled: Boolean,
    @SerialName("manual_transfer_enabled") val manualTransferEnabled: Boolean,
    @SerialName("recipient_account_id") val recipientAccountId: String? = null,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("approved_at") val approvedAt: String? = null,
    @SerialName("activated_at") val activatedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class PaymentCapabilityCreateRequest(
    @SerialName("operator_id") val operatorId: String,
    @SerialName("service_type") val serviceType: String,
    val version: String,
    @SerialName("cash_enabled") val cashEnabled: Boolean = true,
    @SerialName("manual_transfer_enabled") val manualTransferEnabled: Boolean,
    @SerialName("recipient_account_id") val recipientAccountId: String? = null,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
)

@Serializable
data class PaymentCapabilityCommandRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    val reason: String,
)

@Serializable
data class ManualTransferReconciliationRecord(
    @SerialName("claim_id") val claimId: String,
    @SerialName("payment_id") val paymentId: String,
    @SerialName("ride_id") val rideId: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    @SerialName("recipient_account_id") val recipientAccountId: String? = null,
    @SerialName("recipient_label") val recipientLabel: String? = null,
    @SerialName("payment_reference") val paymentReference: String,
    @SerialName("payer_reference") val payerReference: String? = null,
    val amount: String,
    val currency: String,
    val status: String,
    @SerialName("submitted_at") val submittedAt: String,
    @SerialName("reviewed_at") val reviewedAt: String? = null,
)

@Serializable
data class ManualTransferVerifyRequest(
    @SerialName("settlement_reference") val settlementReference: String,
)

@Serializable
data class ManualTransferRejectRequest(val reason: String)

@Serializable
data class PaymentRefundRecord(
    val id: String,
    @SerialName("payment_id") val paymentId: String,
    @SerialName("ride_id") val rideId: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    val amount: String,
    val currency: String,
    val reason: String,
    @SerialName("settlement_method") val settlementMethod: String,
    @SerialName("settlement_reference") val settlementReference: String,
    @SerialName("operator_note") val operatorNote: String,
    @SerialName("driver_recovery_amount") val driverRecoveryAmount: String,
    @SerialName("operator_funded_amount") val operatorFundedAmount: String,
    @SerialName("authorized_by_user_id") val authorizedByUserId: String,
    @SerialName("refunded_at") val refundedAt: String,
    @SerialName("payment_status") val paymentStatus: String,
    @SerialName("remaining_refundable_amount") val remainingRefundableAmount: String,
)

@Serializable
data class PaymentRefundCreateRequest(
    val amount: String,
    val reason: String,
    @SerialName("settlement_method") val settlementMethod: String,
    @SerialName("settlement_reference") val settlementReference: String,
    @SerialName("operator_note") val operatorNote: String,
)

data class PaymentOperationsSnapshot(
    val recipients: PagedResponse<PaymentRecipientRecord>? = null,
    val capabilities: PagedResponse<PaymentCapabilityRecord>? = null,
    val manualTransfers: PagedResponse<ManualTransferReconciliationRecord>? = null,
    val refunds: PagedResponse<PaymentRefundRecord>? = null,
)
