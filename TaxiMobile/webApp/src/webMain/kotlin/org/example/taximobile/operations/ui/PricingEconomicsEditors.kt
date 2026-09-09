package org.example.taximobile.operations.ui

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.OperatorFeePolicyCreateRequest
import org.example.taximobile.operations.model.OperatorFeePolicyRecord
import org.example.taximobile.operations.model.OperatorFeePolicyUpdateRequest
import org.example.taximobile.operations.model.PricingRuleCreateRequest
import org.example.taximobile.operations.model.PricingRuleRecord
import org.example.taximobile.operations.model.PricingRuleUpdateRequest
import org.example.taximobile.operations.model.FixedRouteDirectionRecord
import org.example.taximobile.operations.model.SchedulingPolicyCreateRequest
import org.example.taximobile.operations.model.SchedulingPolicyRecord
import org.example.taximobile.operations.model.SchedulingPolicyUpdateRequest
import org.example.taximobile.operations.model.validCurrency
import org.example.taximobile.operations.model.validMoney
import org.example.taximobile.operations.model.validPercentage
import org.example.taximobile.operations.model.validPolicyVersion
import org.example.taximobile.operations.model.validZonedTimestamp

internal data class TariffDraft(
    val serviceType: String = "ON_DEMAND",
    val fixedRouteDirectionId: String = "",
    val version: String = "",
    val name: String = "",
    val fixedAmount: String = "",
    val currency: String = "MAD",
    val effectiveFrom: String = "",
    val effectiveUntil: String = "",
) {
    fun validationMessage(): String? = when {
        serviceType !in setOf("ON_DEMAND", "FIXED_ROUTE") -> "Choose on-demand or fixed-route service."
        !validPolicyVersion(version) -> "Use a 1–64 character version containing letters, numbers, dots, dashes, or underscores."
        name.trim().length !in 1..120 -> "Enter a tariff name between 1 and 120 characters."
        !validMoney(fixedAmount, allowZero = false) -> "Enter a positive fixed amount with no more than two decimals."
        !validCurrency(currency) -> "Currency must be three uppercase letters."
        !validZonedTimestamp(effectiveFrom) -> "Effective from must be ISO 8601 with Z or an explicit offset."
        effectiveUntil.isNotBlank() && !validZonedTimestamp(effectiveUntil) -> "Effective until must be blank or a zoned ISO 8601 timestamp."
        else -> null
    }

    fun toCreateOrNull(operatorId: String): PricingRuleCreateRequest? {
        if (validationMessage() != null) return null
        return PricingRuleCreateRequest(
            operatorId = operatorId,
            name = name.trim(),
            version = version.trim(),
            fixedAmount = fixedAmount.trim(),
            currency = currency.trim(),
            effectiveFrom = effectiveFrom.trim(),
            effectiveUntil = effectiveUntil.trim().ifBlank { null },
            serviceType = serviceType,
            fixedRouteDirectionId = fixedRouteDirectionId.ifBlank { null },
        )
    }

    fun toUpdateOrNull(existing: PricingRuleRecord): PricingRuleUpdateRequest? {
        if (validationMessage() != null) return null
        return PricingRuleUpdateRequest(
            expectedVersion = existing.optimisticVersion,
            name = name.trim(),
            fixedAmount = fixedAmount.trim(),
            currency = currency.trim(),
            effectiveFrom = effectiveFrom.trim(),
            effectiveUntil = effectiveUntil.trim().ifBlank { null },
            clearEffectiveUntil = existing.effectiveUntil != null && effectiveUntil.isBlank(),
        )
    }

    companion object {
        fun from(record: PricingRuleRecord) = TariffDraft(
            serviceType = record.serviceType,
            fixedRouteDirectionId = record.fixedRouteDirectionId.orEmpty(),
            version = record.version,
            name = record.name,
            fixedAmount = record.fixedAmount.orEmpty(),
            currency = record.currency,
            effectiveFrom = record.effectiveFrom,
            effectiveUntil = record.effectiveUntil.orEmpty(),
        )
    }
}

internal data class FeePolicyDraft(
    val serviceType: String = "ON_DEMAND",
    val version: String = "",
    val calculationMode: String = "PERCENTAGE_OF_TRANSPORT_FARE",
    val fundingMode: String = "DRIVER_SETTLEMENT_DEDUCTION",
    val percentageRate: String = "",
    val flatAmount: String = "",
    val currency: String = "MAD",
    val minimumDriverNet: String = "0.00",
    val effectiveFrom: String = "",
    val effectiveUntil: String = "",
) {
    fun validationMessage(): String? = when {
        serviceType !in setOf("ON_DEMAND", "FIXED_ROUTE") -> "Choose on-demand or fixed-route service."
        !validPolicyVersion(version) -> "Use a valid 1–64 character policy version."
        calculationMode == "PERCENTAGE_OF_TRANSPORT_FARE" && !validPercentage(percentageRate) ->
            "Enter a percentage from 0 through 99.9999 with no more than four decimals."
        calculationMode == "FLAT_PER_COMPLETED_BOOKING" && !validMoney(flatAmount, allowZero = true) ->
            "Enter a non-negative flat amount with no more than two decimals."
        calculationMode !in setOf("PERCENTAGE_OF_TRANSPORT_FARE", "FLAT_PER_COMPLETED_BOOKING") ->
            "Choose one documented calculation mode."
        fundingMode !in setOf("DRIVER_SETTLEMENT_DEDUCTION", "PASSENGER_SURCHARGE") ->
            "Choose one documented funding mode."
        !validCurrency(currency) -> "Currency must be three uppercase letters."
        !validMoney(minimumDriverNet, allowZero = true) -> "Enter a non-negative minimum driver net."
        !validZonedTimestamp(effectiveFrom) -> "Effective from must be ISO 8601 with Z or an explicit offset."
        effectiveUntil.isNotBlank() && !validZonedTimestamp(effectiveUntil) -> "Effective until must be blank or a zoned ISO 8601 timestamp."
        else -> null
    }

    fun toCreateOrNull(operatorId: String): OperatorFeePolicyCreateRequest? {
        if (validationMessage() != null) return null
        return OperatorFeePolicyCreateRequest(
            operatorId = operatorId,
            version = version.trim(),
            calculationMode = calculationMode,
            fundingMode = fundingMode,
            percentageRate = percentageRate.trim().takeIf { calculationMode == "PERCENTAGE_OF_TRANSPORT_FARE" },
            flatAmount = flatAmount.trim().takeIf { calculationMode == "FLAT_PER_COMPLETED_BOOKING" },
            currency = currency.trim(),
            minimumDriverNet = minimumDriverNet.trim(),
            effectiveFrom = effectiveFrom.trim(),
            effectiveUntil = effectiveUntil.trim().ifBlank { null },
            serviceType = serviceType,
        )
    }

    fun toUpdateOrNull(existing: OperatorFeePolicyRecord): OperatorFeePolicyUpdateRequest? {
        if (validationMessage() != null) return null
        return OperatorFeePolicyUpdateRequest(
            expectedVersion = existing.optimisticVersion,
            calculationMode = calculationMode,
            fundingMode = fundingMode,
            percentageRate = percentageRate.trim().takeIf { calculationMode == "PERCENTAGE_OF_TRANSPORT_FARE" },
            flatAmount = flatAmount.trim().takeIf { calculationMode == "FLAT_PER_COMPLETED_BOOKING" },
            currency = currency.trim(),
            minimumDriverNet = minimumDriverNet.trim(),
            effectiveFrom = effectiveFrom.trim(),
            effectiveUntil = effectiveUntil.trim().ifBlank { null },
            clearEffectiveUntil = existing.effectiveUntil != null && effectiveUntil.isBlank(),
        )
    }

    companion object {
        fun from(record: OperatorFeePolicyRecord) = FeePolicyDraft(
            serviceType = record.serviceType,
            version = record.version,
            calculationMode = record.calculationMode,
            fundingMode = record.fundingMode,
            percentageRate = record.percentageRate.orEmpty(),
            flatAmount = record.flatAmount.orEmpty(),
            currency = record.currency,
            minimumDriverNet = record.minimumDriverNet,
            effectiveFrom = record.effectiveFrom,
            effectiveUntil = record.effectiveUntil.orEmpty(),
        )
    }
}

internal data class SchedulingPolicyDraft(
    val serviceType: String = "ON_DEMAND",
    val version: String = "",
    val surchargeAmount: String = "0.00",
    val currency: String = "MAD",
    val beneficiary: String = "DRIVER",
    val minimumLeadMinutes: String = "60",
    val maximumHorizonDays: String = "30",
    val offerOpenMinutesBefore: String = "1440",
    val offerResponseSeconds: String = "120",
    val commitmentDeadlineMinutesBefore: String = "180",
    val handoffMinutesBefore: String = "30",
    val protectedDurationMinutes: String = "90",
    val conflictBufferBeforeMinutes: String = "30",
    val conflictBufferAfterMinutes: String = "30",
    val passengerCancelCutoffMinutes: String = "60",
    val driverCancelCutoffMinutes: String = "120",
    val surchargeRefundMode: String = "FULL_BEFORE_CUTOFF",
    val fallbackMatchingEnabled: Boolean = true,
    val effectiveFrom: String = "",
    val effectiveUntil: String = "",
) {
    fun validationMessage(): String? = when {
        serviceType !in setOf("ON_DEMAND", "FIXED_ROUTE") -> "Choose on-demand or fixed-route service."
        !validPolicyVersion(version) -> "Use a valid 1–64 character policy version."
        !validMoney(surchargeAmount, allowZero = true) -> "Enter a non-negative surcharge with no more than two decimals."
        !validCurrency(currency) -> "Currency must be three uppercase letters."
        beneficiary !in setOf("DRIVER", "OPERATOR") -> "Choose the explicit surcharge beneficiary."
        integerOutside(minimumLeadMinutes, 15, 10080) -> "Minimum lead must be 15–10080 minutes."
        integerOutside(maximumHorizonDays, 1, 365) -> "Maximum horizon must be 1–365 days."
        integerOutside(offerOpenMinutesBefore, 30, 43200) -> "Offer opening must be 30–43200 minutes before pickup."
        integerOutside(offerResponseSeconds, 15, 3600) -> "Offer response must be 15–3600 seconds."
        integerOutside(commitmentDeadlineMinutesBefore, 10, 10080) -> "Commitment deadline must be 10–10080 minutes before pickup."
        integerOutside(handoffMinutesBefore, 5, 1440) -> "Handoff must be 5–1440 minutes before pickup."
        offerOpenMinutesBefore.toInt() <= commitmentDeadlineMinutesBefore.toInt() ||
            commitmentDeadlineMinutesBefore.toInt() < handoffMinutesBefore.toInt() ->
            "Offer opening must precede the commitment deadline, which cannot be after handoff."
        integerOutside(protectedDurationMinutes, 15, 1440) -> "Protected duration must be 15–1440 minutes."
        integerOutside(conflictBufferBeforeMinutes, 0, 1440) -> "Before buffer must be 0–1440 minutes."
        integerOutside(conflictBufferAfterMinutes, 0, 1440) -> "After buffer must be 0–1440 minutes."
        integerOutside(passengerCancelCutoffMinutes, 0, 10080) -> "Passenger cutoff must be 0–10080 minutes."
        integerOutside(driverCancelCutoffMinutes, 0, 10080) -> "Driver cutoff must be 0–10080 minutes."
        surchargeRefundMode !in setOf("ALWAYS_FULL", "FULL_BEFORE_CUTOFF", "NON_REFUNDABLE") ->
            "Choose a documented surcharge refund rule."
        !validZonedTimestamp(effectiveFrom) -> "Effective from must be ISO 8601 with Z or an explicit offset."
        effectiveUntil.isNotBlank() && !validZonedTimestamp(effectiveUntil) -> "Effective until must be blank or a zoned ISO 8601 timestamp."
        else -> null
    }

    fun toCreateOrNull(operatorId: String): SchedulingPolicyCreateRequest? {
        if (validationMessage() != null) return null
        return SchedulingPolicyCreateRequest(
            operatorId = operatorId,
            version = version.trim(),
            surchargeAmount = surchargeAmount.trim(),
            currency = currency.trim(),
            beneficiary = beneficiary,
            effectiveFrom = effectiveFrom.trim(),
            effectiveUntil = effectiveUntil.trim().ifBlank { null },
            serviceType = serviceType,
            minimumLeadMinutes = minimumLeadMinutes.toInt(),
            maximumHorizonDays = maximumHorizonDays.toInt(),
            offerOpenMinutesBefore = offerOpenMinutesBefore.toInt(),
            offerResponseSeconds = offerResponseSeconds.toInt(),
            commitmentDeadlineMinutesBefore = commitmentDeadlineMinutesBefore.toInt(),
            handoffMinutesBefore = handoffMinutesBefore.toInt(),
            protectedDurationMinutes = protectedDurationMinutes.toInt(),
            conflictBufferBeforeMinutes = conflictBufferBeforeMinutes.toInt(),
            conflictBufferAfterMinutes = conflictBufferAfterMinutes.toInt(),
            passengerCancelCutoffMinutes = passengerCancelCutoffMinutes.toInt(),
            driverCancelCutoffMinutes = driverCancelCutoffMinutes.toInt(),
            surchargeRefundMode = surchargeRefundMode,
            fallbackMatchingEnabled = fallbackMatchingEnabled,
        )
    }

    fun toUpdateOrNull(existing: SchedulingPolicyRecord): SchedulingPolicyUpdateRequest? {
        if (validationMessage() != null) return null
        return SchedulingPolicyUpdateRequest(
            expectedVersion = existing.optimisticVersion,
            surchargeAmount = surchargeAmount.trim(),
            currency = currency.trim(),
            beneficiary = beneficiary,
            minimumLeadMinutes = minimumLeadMinutes.toInt(),
            maximumHorizonDays = maximumHorizonDays.toInt(),
            offerOpenMinutesBefore = offerOpenMinutesBefore.toInt(),
            offerResponseSeconds = offerResponseSeconds.toInt(),
            commitmentDeadlineMinutesBefore = commitmentDeadlineMinutesBefore.toInt(),
            handoffMinutesBefore = handoffMinutesBefore.toInt(),
            protectedDurationMinutes = protectedDurationMinutes.toInt(),
            conflictBufferBeforeMinutes = conflictBufferBeforeMinutes.toInt(),
            conflictBufferAfterMinutes = conflictBufferAfterMinutes.toInt(),
            passengerCancelCutoffMinutes = passengerCancelCutoffMinutes.toInt(),
            driverCancelCutoffMinutes = driverCancelCutoffMinutes.toInt(),
            surchargeRefundMode = surchargeRefundMode,
            fallbackMatchingEnabled = fallbackMatchingEnabled,
            effectiveFrom = effectiveFrom.trim(),
            effectiveUntil = effectiveUntil.trim().ifBlank { null },
            clearEffectiveUntil = existing.effectiveUntil != null && effectiveUntil.isBlank(),
        )
    }

    companion object {
        fun from(record: SchedulingPolicyRecord) = SchedulingPolicyDraft(
            serviceType = record.serviceType,
            version = record.version,
            surchargeAmount = record.surchargeAmount,
            currency = record.currency,
            beneficiary = record.beneficiary,
            minimumLeadMinutes = record.minimumLeadMinutes.toString(),
            maximumHorizonDays = record.maximumHorizonDays.toString(),
            offerOpenMinutesBefore = record.offerOpenMinutesBefore.toString(),
            offerResponseSeconds = record.offerResponseSeconds.toString(),
            commitmentDeadlineMinutesBefore = record.commitmentDeadlineMinutesBefore.toString(),
            handoffMinutesBefore = record.handoffMinutesBefore.toString(),
            protectedDurationMinutes = record.protectedDurationMinutes.toString(),
            conflictBufferBeforeMinutes = record.conflictBufferBeforeMinutes.toString(),
            conflictBufferAfterMinutes = record.conflictBufferAfterMinutes.toString(),
            passengerCancelCutoffMinutes = record.passengerCancelCutoffMinutes.toString(),
            driverCancelCutoffMinutes = record.driverCancelCutoffMinutes.toString(),
            surchargeRefundMode = record.surchargeRefundMode,
            fallbackMatchingEnabled = record.fallbackMatchingEnabled,
            effectiveFrom = record.effectiveFrom,
            effectiveUntil = record.effectiveUntil.orEmpty(),
        )
    }
}

private fun integerOutside(value: String, minimum: Int, maximum: Int): Boolean =
    value.toIntOrNull()?.let { it !in minimum..maximum } ?: true

@Composable
internal fun TariffEditor(
    existing: PricingRuleRecord?,
    fixedRouteDirections: List<FixedRouteDirectionRecord>,
    operatorId: String,
    currencyHint: String,
    locked: Boolean,
    onCreate: (PricingRuleCreateRequest) -> Unit,
    onUpdate: (PricingRuleRecord, PricingRuleUpdateRequest) -> Unit,
    onClose: () -> Unit,
) {
    var draft by remember(existing?.id, operatorId) {
        mutableStateOf(existing?.let(TariffDraft::from) ?: TariffDraft(currency = currencyHint))
    }
    PolicyEditorFrame(if (existing == null) "Create tariff draft" else "Edit tariff ${existing.version}", onClose, locked) {
        PolicyChoice("Service", draft.serviceType, listOf(
            "ON_DEMAND" to "On-demand",
            "FIXED_ROUTE" to "Fixed route",
        ), locked || existing != null) { draft = draft.copy(serviceType = it) }
        if (draft.serviceType == "FIXED_ROUTE") {
            val selectedDirection = fixedRouteDirections.firstOrNull { it.id == draft.fixedRouteDirectionId }
            ScopeMenu(
                label = "Immutable route direction",
                selected = selectedDirection?.let {
                    "${it.startLocationName.preferred()} → ${it.finishLocationName.preferred()} · ${it.id}"
                } ?: if (draft.fixedRouteDirectionId.isBlank()) "Link later in Fixed routes" else draft.fixedRouteDirectionId,
                options = listOf(ScopeOption("", "Link later in Fixed routes")) +
                    fixedRouteDirections.map {
                        ScopeOption(
                            it.id,
                            "${it.startLocationName.preferred()} → ${it.finishLocationName.preferred()} · ${it.id}",
                        )
                    },
                enabled = !locked && existing == null,
                onSelected = { draft = draft.copy(fixedRouteDirectionId = it.orEmpty()) },
            )
            Text(
                "A fixed-route fare may be drafted unbound, but activation fails until exactly one draft direction links back to it.",
                color = TaxiColors.Ink500,
                style = MaterialTheme.typography.bodySmall,
            )
        }
        PolicyField("Version", draft.version, !locked && existing == null) { draft = draft.copy(version = it.take(64)) }
        PolicyField("Name", draft.name, !locked) { draft = draft.copy(name = it.take(120)) }
        PolicyField("Fixed transport fare", draft.fixedAmount, !locked) { draft = draft.copy(fixedAmount = it.take(16)) }
        PolicyField("Currency", draft.currency, !locked) { draft = draft.copy(currency = it.uppercase().take(3)) }
        EffectiveFields(draft.effectiveFrom, draft.effectiveUntil, locked,
            { draft = draft.copy(effectiveFrom = it) }, { draft = draft.copy(effectiveUntil = it) })
        ValidationAndSave(draft.validationMessage(), locked) {
            if (existing == null) draft.toCreateOrNull(operatorId)?.let(onCreate)
            else draft.toUpdateOrNull(existing)?.let { onUpdate(existing, it) }
        }
    }
}

@Composable
internal fun FeePolicyEditor(
    existing: OperatorFeePolicyRecord?,
    operatorId: String,
    currencyHint: String,
    locked: Boolean,
    onCreate: (OperatorFeePolicyCreateRequest) -> Unit,
    onUpdate: (OperatorFeePolicyRecord, OperatorFeePolicyUpdateRequest) -> Unit,
    onClose: () -> Unit,
) {
    var draft by remember(existing?.id, operatorId) {
        mutableStateOf(existing?.let(FeePolicyDraft::from) ?: FeePolicyDraft(currency = currencyHint))
    }
    PolicyEditorFrame(if (existing == null) "Create operator-fee draft" else "Edit fee policy ${existing.version}", onClose, locked) {
        PolicyChoice("Service", draft.serviceType, listOf(
            "ON_DEMAND" to "On-demand",
            "FIXED_ROUTE" to "Fixed route",
        ), locked || existing != null) { draft = draft.copy(serviceType = it) }
        PolicyField("Version", draft.version, !locked && existing == null) { draft = draft.copy(version = it.take(64)) }
        PolicyChoice("Calculation mode", draft.calculationMode, listOf(
            "PERCENTAGE_OF_TRANSPORT_FARE" to "Percentage of transport fare",
            "FLAT_PER_COMPLETED_BOOKING" to "Flat per completed booking",
        ), locked) { draft = draft.copy(calculationMode = it) }
        if (draft.calculationMode == "PERCENTAGE_OF_TRANSPORT_FARE") {
            PolicyField("Percentage rate", draft.percentageRate, !locked) { draft = draft.copy(percentageRate = it.take(10)) }
        } else {
            PolicyField("Flat amount", draft.flatAmount, !locked) { draft = draft.copy(flatAmount = it.take(16)) }
        }
        PolicyChoice("Funding", draft.fundingMode, listOf(
            "DRIVER_SETTLEMENT_DEDUCTION" to "Driver settlement deduction",
            "PASSENGER_SURCHARGE" to "Passenger surcharge",
        ), locked) { draft = draft.copy(fundingMode = it) }
        PolicyField("Currency", draft.currency, !locked) { draft = draft.copy(currency = it.uppercase().take(3)) }
        PolicyField("Minimum driver net", draft.minimumDriverNet, !locked) { draft = draft.copy(minimumDriverNet = it.take(16)) }
        Text("Eligible base: TRANSPORT_FARE · rounding: HALF_UP_0_01", color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
        EffectiveFields(draft.effectiveFrom, draft.effectiveUntil, locked,
            { draft = draft.copy(effectiveFrom = it) }, { draft = draft.copy(effectiveUntil = it) })
        ValidationAndSave(draft.validationMessage(), locked) {
            if (existing == null) draft.toCreateOrNull(operatorId)?.let(onCreate)
            else draft.toUpdateOrNull(existing)?.let { onUpdate(existing, it) }
        }
    }
}

@Composable
internal fun SchedulingPolicyEditor(
    existing: SchedulingPolicyRecord?,
    operatorId: String,
    currencyHint: String,
    locked: Boolean,
    onCreate: (SchedulingPolicyCreateRequest) -> Unit,
    onUpdate: (SchedulingPolicyRecord, SchedulingPolicyUpdateRequest) -> Unit,
    onClose: () -> Unit,
) {
    var draft by remember(existing?.id, operatorId) {
        mutableStateOf(existing?.let(SchedulingPolicyDraft::from) ?: SchedulingPolicyDraft(currency = currencyHint))
    }
    PolicyEditorFrame(if (existing == null) "Create scheduling-policy draft" else "Edit scheduling policy ${existing.version}", onClose, locked) {
        PolicyChoice("Service", draft.serviceType, listOf(
            "ON_DEMAND" to "On-demand",
            "FIXED_ROUTE" to "Fixed route",
        ), locked || existing != null) { draft = draft.copy(serviceType = it) }
        PolicyField("Version", draft.version, !locked && existing == null) { draft = draft.copy(version = it.take(64)) }
        PolicyField("Scheduling surcharge", draft.surchargeAmount, !locked) { draft = draft.copy(surchargeAmount = it.take(16)) }
        PolicyField("Currency", draft.currency, !locked) { draft = draft.copy(currency = it.uppercase().take(3)) }
        PolicyChoice("Beneficiary", draft.beneficiary, listOf("DRIVER" to "Driver", "OPERATOR" to "Operator"), locked) {
            draft = draft.copy(beneficiary = it)
        }
        Text("Collection timing: AT_RIDE_SETTLEMENT", color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
        Text("Booking windows", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        PolicyField("Minimum lead (minutes)", draft.minimumLeadMinutes, !locked) { draft = draft.copy(minimumLeadMinutes = it.filter(Char::isDigit).take(5)) }
        PolicyField("Maximum horizon (days)", draft.maximumHorizonDays, !locked) { draft = draft.copy(maximumHorizonDays = it.filter(Char::isDigit).take(3)) }
        PolicyField("Open offers before pickup (minutes)", draft.offerOpenMinutesBefore, !locked) { draft = draft.copy(offerOpenMinutesBefore = it.filter(Char::isDigit).take(5)) }
        PolicyField("Driver response window (seconds)", draft.offerResponseSeconds, !locked) { draft = draft.copy(offerResponseSeconds = it.filter(Char::isDigit).take(4)) }
        PolicyField("Commitment deadline before pickup (minutes)", draft.commitmentDeadlineMinutesBefore, !locked) { draft = draft.copy(commitmentDeadlineMinutesBefore = it.filter(Char::isDigit).take(5)) }
        PolicyField("Dispatch handoff before pickup (minutes)", draft.handoffMinutesBefore, !locked) { draft = draft.copy(handoffMinutesBefore = it.filter(Char::isDigit).take(4)) }
        Text("Conflict protection and cancellation", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        PolicyField("Protected ride duration (minutes)", draft.protectedDurationMinutes, !locked) { draft = draft.copy(protectedDurationMinutes = it.filter(Char::isDigit).take(4)) }
        PolicyField("Conflict buffer before (minutes)", draft.conflictBufferBeforeMinutes, !locked) { draft = draft.copy(conflictBufferBeforeMinutes = it.filter(Char::isDigit).take(4)) }
        PolicyField("Conflict buffer after (minutes)", draft.conflictBufferAfterMinutes, !locked) { draft = draft.copy(conflictBufferAfterMinutes = it.filter(Char::isDigit).take(4)) }
        PolicyField("Passenger cancellation cutoff (minutes)", draft.passengerCancelCutoffMinutes, !locked) { draft = draft.copy(passengerCancelCutoffMinutes = it.filter(Char::isDigit).take(5)) }
        PolicyField("Driver cancellation cutoff (minutes)", draft.driverCancelCutoffMinutes, !locked) { draft = draft.copy(driverCancelCutoffMinutes = it.filter(Char::isDigit).take(5)) }
        PolicyChoice("Surcharge refund rule", draft.surchargeRefundMode, listOf(
            "ALWAYS_FULL" to "Always full",
            "FULL_BEFORE_CUTOFF" to "Full before cutoff",
            "NON_REFUNDABLE" to "Non-refundable",
        ), locked) { draft = draft.copy(surchargeRefundMode = it) }
        PolicyChoice("Handoff fallback matching", draft.fallbackMatchingEnabled.toString(), listOf(
            "true" to "Enabled",
            "false" to "Disabled",
        ), locked) { draft = draft.copy(fallbackMatchingEnabled = it == "true") }
        EffectiveFields(draft.effectiveFrom, draft.effectiveUntil, locked,
            { draft = draft.copy(effectiveFrom = it) }, { draft = draft.copy(effectiveUntil = it) })
        ValidationAndSave(draft.validationMessage(), locked) {
            if (existing == null) draft.toCreateOrNull(operatorId)?.let(onCreate)
            else draft.toUpdateOrNull(existing)?.let { onUpdate(existing, it) }
        }
    }
}

@Composable
private fun PolicyEditorFrame(
    title: String,
    onClose: () -> Unit,
    locked: Boolean,
    content: @Composable ColumnScope.() -> Unit,
) {
    DataCard {
        Column(
            Modifier.fillMaxWidth().padding(TaxiSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                TextButton(onClick = onClose, enabled = !locked) { Text("Close") }
            }
            Text(
                "Times require a timezone, for example 2026-08-27T12:00:00Z. The backend validates range overlap, assignment, currency, and activation readiness.",
                color = TaxiColors.Ink500,
                style = MaterialTheme.typography.bodySmall,
            )
            content()
        }
    }
}

@Composable
private fun PolicyField(label: String, value: String, enabled: Boolean, onValue: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onValue,
        modifier = Modifier.fillMaxWidth(),
        label = { Text(label) },
        enabled = enabled,
        singleLine = true,
    )
}

@Composable
private fun EffectiveFields(
    effectiveFrom: String,
    effectiveUntil: String,
    locked: Boolean,
    onFrom: (String) -> Unit,
    onUntil: (String) -> Unit,
) {
    PolicyField("Effective from (ISO 8601)", effectiveFrom, !locked) { onFrom(it.take(40)) }
    PolicyField("Effective until (optional)", effectiveUntil, !locked) { onUntil(it.take(40)) }
}

@Composable
private fun PolicyChoice(
    label: String,
    selected: String,
    options: List<Pair<String, String>>,
    locked: Boolean,
    onSelected: (String) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
        Text(label, style = MaterialTheme.typography.labelMedium, color = TaxiColors.Ink500)
        Row(
            Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            options.forEach { (value, display) ->
                if (value == selected) {
                    Button(onClick = { onSelected(value) }, enabled = !locked) { Text(display) }
                } else {
                    OutlinedButton(onClick = { onSelected(value) }, enabled = !locked) { Text(display) }
                }
            }
        }
    }
}

@Composable
private fun ValidationAndSave(message: String?, locked: Boolean, onSave: () -> Unit) {
    Text(
        message ?: "Ready to send for backend validation.",
        color = if (message == null) TaxiColors.Success600 else TaxiColors.Warning600,
        style = MaterialTheme.typography.bodySmall,
    )
    Button(onClick = onSave, enabled = message == null && !locked) { Text("Save draft") }
}
