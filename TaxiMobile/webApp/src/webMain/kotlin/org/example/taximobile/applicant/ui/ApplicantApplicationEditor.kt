package org.example.taximobile.applicant.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.intl.Locale
import androidx.compose.ui.unit.dp
import org.example.taximobile.domain.drivers.DriverApplicationAnswerDraft
import org.example.taximobile.domain.drivers.DriverApplicationEvidenceDraft
import org.example.taximobile.domain.drivers.DriverApplicationDocument
import org.example.taximobile.domain.drivers.DriverCityApplication
import org.example.taximobile.domain.drivers.DriverCredential
import org.example.taximobile.domain.drivers.DriverRequirement
import org.example.taximobile.domain.drivers.DriverRequirementEvidenceType
import org.example.taximobile.domain.drivers.DriverVehicle
import org.example.taximobile.domain.drivers.VehicleRegistration
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.driver.onboarding.CityAuthorizationSummary

@Composable
internal fun ApplicantApplicationEditor(
    application: DriverCityApplication,
    vehicles: List<DriverVehicle>,
    credentials: List<DriverCredential>,
    locked: Boolean,
    onSave: (
        applicationId: String,
        expectedVersion: Int,
        answers: List<DriverApplicationAnswerDraft>,
        evidence: List<DriverApplicationEvidenceDraft>,
        removeAnswerItemIds: List<String>,
        removeEvidenceItemIds: List<String>,
    ) -> Unit,
    onSubmit: (String) -> Unit,
    onWithdraw: (String) -> Unit,
    documentPickerAvailable: Boolean,
    onUploadDocument: (String, String, Int) -> Unit,
    onDeleteDocument: (String, String, Int) -> Unit,
    onRegisterVehicle: (VehicleRegistration) -> Unit,
) {
    val language = Locale.current.language
    val draftKey = "${application.id}:${application.optimisticVersion}"
    val textValues = remember(draftKey) {
        mutableStateMapOf<String, String>().apply {
            application.answers.forEach { answer ->
                answer.textValue?.let { put(answer.requirementItemId, it) }
                answer.dateValue?.let { put(answer.requirementItemId, it) }
            }
        }
    }
    val booleanValues = remember(draftKey) {
        mutableStateMapOf<String, Boolean>().apply {
            application.answers.forEach { answer ->
                answer.booleanValue?.let { put(answer.requirementItemId, it) }
            }
        }
    }
    val selectedVehicles = remember(draftKey) {
        mutableStateMapOf<String, String>().apply {
            application.evidence.forEach { evidence ->
                evidence.vehicleId?.let { put(evidence.requirementItemId, it) }
            }
        }
    }
    val selectedCredentials = remember(draftKey) {
        mutableStateMapOf<String, String>().apply {
            application.evidence.forEach { evidence ->
                evidence.credentialId?.let { put(evidence.requirementItemId, it) }
            }
        }
    }
    var confirmWithdrawal by remember(application.id) { mutableStateOf(false) }

    HorizontalDivider(color = TaxiColors.StrokeSubtle)
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically) {
        Column {
            Text(application.cityName.forLanguage(language), style = MaterialTheme.typography.headlineSmall,
                color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
            Text("City-scoped application · requirements ${application.requirementVersion}",
                color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
        }
        ApplicantStatus(application.status)
    }

    ApplicationTimeline(application.status)

    application.latestDecision?.let { decision ->
        ApplicantCard {
            Text("Latest reviewer message", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
            Text(decision.message)
            Text("Reason: ${decision.reasonCode.toDisplayLabel()}", color = TaxiColors.Ink500,
                style = MaterialTheme.typography.bodySmall)
        }
    }
    application.authorization?.let { authorization ->
        ApplicantCard(selected = authorization.status == "ACTIVE") {
            CityAuthorizationSummary(authorization.status, authorization.validUntil)
            Text("Services: ${authorization.serviceTypes.joinToString { it.toDisplayLabel() }}")
            if (!authorization.scheduledOffersEnabled) {
                Text("Scheduled offers are not enabled for this authorization.", color = TaxiColors.Ink500)
            }
        }
    }

    Text("Application requirements", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    application.requirements.sortedBy { it.displayOrder }.forEach { requirement ->
        ApplicantRequirementEditor(
            requirement = requirement,
            missing = requirement.id in application.missingRequiredItemIds,
            editable = application.editable && !locked,
            textValue = textValues[requirement.id].orEmpty(),
            booleanValue = booleanValues[requirement.id] ?: false,
            selectedVehicleId = selectedVehicles[requirement.id],
            selectedCredentialId = selectedCredentials[requirement.id],
            vehicles = vehicles,
            credentials = credentials.filter { requirement.referenceType == null || it.type == requirement.referenceType },
            documentUploadAvailable = application.documentUploadAvailable,
            documentPickerAvailable = documentPickerAvailable,
            document = application.documents.firstOrNull {
                it.requirementItemId == requirement.id
            },
            onUploadDocument = {
                onUploadDocument(
                    application.id,
                    requirement.id,
                    application.optimisticVersion,
                )
            },
            onDeleteDocument = { documentId ->
                onDeleteDocument(
                    application.id,
                    documentId,
                    application.optimisticVersion,
                )
            },
            onText = { textValues[requirement.id] = it },
            onBoolean = { booleanValues[requirement.id] = it },
            onVehicle = { id ->
                if (selectedVehicles[requirement.id] == id) selectedVehicles.remove(requirement.id)
                else selectedVehicles[requirement.id] = id
            },
            onCredential = { id ->
                if (selectedCredentials[requirement.id] == id) selectedCredentials.remove(requirement.id)
                else selectedCredentials[requirement.id] = id
            },
        )
    }

    if (application.editable && application.requirements.any { it.evidenceType == DriverRequirementEvidenceType.VEHICLE }) {
        ApplicantVehicleForm(locked = locked, onRegister = onRegisterVehicle)
    }

    if (application.editable) {
        val answers = application.requirements.mapNotNull { requirement ->
            when (requirement.evidenceType) {
                DriverRequirementEvidenceType.BOOLEAN -> DriverApplicationAnswerDraft(
                    requirementItemId = requirement.id,
                    answerType = "BOOLEAN",
                    booleanValue = booleanValues[requirement.id] ?: false,
                )
                DriverRequirementEvidenceType.DATE -> textValues[requirement.id]?.trim()
                    ?.takeIf(String::isNotEmpty)
                    ?.let { DriverApplicationAnswerDraft(requirement.id, "DATE", dateValue = it) }
                DriverRequirementEvidenceType.TEXT -> textValues[requirement.id]?.trim()
                    ?.takeIf(String::isNotEmpty)
                    ?.let { DriverApplicationAnswerDraft(requirement.id, "TEXT", textValue = it) }
                else -> null
            }
        }
        val evidence = buildList {
            selectedVehicles.forEach { (itemId, vehicleId) ->
                add(DriverApplicationEvidenceDraft(itemId, vehicleId = vehicleId))
            }
            selectedCredentials.forEach { (itemId, credentialId) ->
                add(DriverApplicationEvidenceDraft(itemId, credentialId = credentialId))
            }
        }
        val answerIds = answers.mapTo(mutableSetOf()) { it.requirementItemId }
        val evidenceIds = evidence.mapTo(mutableSetOf()) { it.requirementItemId }
        val removeAnswerIds = application.answers.map { it.requirementItemId }.filter { id ->
            id !in answerIds && application.requirements.any {
                it.id == id && it.evidenceType in setOf(DriverRequirementEvidenceType.DATE, DriverRequirementEvidenceType.TEXT)
            }
        }
        val removeEvidenceIds = application.evidence.map { it.requirementItemId }.filter { id ->
            id !in evidenceIds && application.requirements.any {
                it.id == id && it.evidenceType in setOf(
                    DriverRequirementEvidenceType.VEHICLE,
                    DriverRequirementEvidenceType.CREDENTIAL,
                )
            }
        }
        ApplicantPrimaryButton(
            "Save draft",
            onClick = {
                onSave(
                    application.id,
                    application.optimisticVersion,
                    answers,
                    evidence,
                    removeAnswerIds,
                    removeEvidenceIds,
                )
            },
            enabled = !locked,
        )
        Surface(
            color = if (application.complete) TaxiColors.Success100 else TaxiColors.Warning100,
            shape = RoundedCornerShape(TaxiRadii.Md),
        ) {
            Text(
                if (application.complete) "The backend confirms all required items are complete."
                else "Required items are still missing. Save the draft, then review the updated status.",
                Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                color = if (application.complete) TaxiColors.Success600 else TaxiColors.Warning600,
            )
        }
        ApplicantPrimaryButton(
            "Submit for city review",
            onClick = { onSubmit(application.id) },
            enabled = application.complete && !locked,
        )
    }

    if (application.status in WITHDRAWABLE_STATUSES) {
        OutlinedButton(onClick = { confirmWithdrawal = true }, enabled = !locked, modifier = Modifier.fillMaxWidth()) {
            Text("Withdraw application", color = TaxiColors.Danger600)
        }
    }
    if (confirmWithdrawal) {
        ApplicantCard {
            Text("Withdraw this city application?", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text("The record and status remain visible. This does not delete documents or your account.")
            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                OutlinedButton(onClick = { confirmWithdrawal = false }) { Text("Keep application") }
                OutlinedButton(
                    onClick = {
                        confirmWithdrawal = false
                        onWithdraw(application.id)
                    },
                    enabled = !locked,
                ) { Text("Confirm withdrawal", color = TaxiColors.Danger600) }
            }
        }
    }
}

@Composable
private fun ApplicantRequirementEditor(
    requirement: DriverRequirement,
    missing: Boolean,
    editable: Boolean,
    textValue: String,
    booleanValue: Boolean,
    selectedVehicleId: String?,
    selectedCredentialId: String?,
    vehicles: List<DriverVehicle>,
    credentials: List<DriverCredential>,
    documentUploadAvailable: Boolean,
    documentPickerAvailable: Boolean,
    document: DriverApplicationDocument?,
    onUploadDocument: () -> Unit,
    onDeleteDocument: (String) -> Unit,
    onText: (String) -> Unit,
    onBoolean: (Boolean) -> Unit,
    onVehicle: (String) -> Unit,
    onCredential: (String) -> Unit,
) {
    val language = Locale.current.language
    ApplicantCard(selected = missing) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(requirement.label.forLanguage(language), Modifier.weight(1f), fontWeight = FontWeight.Bold)
            Text(if (missing) "Missing" else if (requirement.required) "Required" else "Optional",
                color = if (missing) TaxiColors.Warning600 else TaxiColors.Ink500,
                style = MaterialTheme.typography.labelMedium)
        }
        Text(requirement.description.forLanguage(language), color = TaxiColors.Ink500)
        when (requirement.evidenceType) {
            DriverRequirementEvidenceType.PROFILE -> Text("Your signed-in profile is linked automatically.", color = TaxiColors.Success600)
            DriverRequirementEvidenceType.BOOLEAN -> Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(booleanValue, onCheckedChange = onBoolean, enabled = editable)
                Text("I confirm this requirement")
            }
            DriverRequirementEvidenceType.DATE -> OutlinedTextField(
                textValue,
                { onText(it.take(10)) },
                Modifier.fillMaxWidth(),
                label = { Text("Date (YYYY-MM-DD)") },
                singleLine = true,
                enabled = editable,
            )
            DriverRequirementEvidenceType.TEXT -> OutlinedTextField(
                textValue,
                { onText(it.take(1000)) },
                Modifier.fillMaxWidth(),
                label = { Text("Your answer") },
                enabled = editable,
            )
            DriverRequirementEvidenceType.VEHICLE -> EvidenceChoices(
                "Select a vehicle",
                vehicles.map { it.id to "${it.make} ${it.model} · ${it.verificationStatus.toDisplayLabel()}" },
                selectedVehicleId,
                editable,
                onVehicle,
            )
            DriverRequirementEvidenceType.CREDENTIAL -> EvidenceChoices(
                "Select a professional credential",
                credentials.map { it.id to "${it.type.toDisplayLabel()} · ${it.status.toDisplayLabel()}" },
                selectedCredentialId,
                editable,
                onCredential,
            )
            DriverRequirementEvidenceType.DOCUMENT -> {
                Surface(
                    color = if (document == null) TaxiColors.Warning100 else TaxiColors.Success100,
                    shape = RoundedCornerShape(TaxiRadii.Md),
                    border = BorderStroke(
                        1.dp,
                        if (document == null) TaxiColors.Warning600.copy(alpha = 0.25f)
                        else TaxiColors.Success600.copy(alpha = 0.25f),
                    ),
                ) {
                    Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md)) {
                        Text(
                            when {
                                document != null -> "Protected document · ${document.scanStatus.toDisplayLabel()}"
                                documentUploadAvailable && documentPickerAvailable -> "Ready for protected upload"
                                else -> "Protected document upload unavailable"
                            },
                            fontWeight = FontWeight.Bold,
                            color = if (document == null) TaxiColors.Warning600 else TaxiColors.Success600,
                        )
                        Text(
                            when {
                                document != null -> "${document.mediaType} · ${document.byteSize} bytes"
                                !documentUploadAvailable -> "Protected storage is not configured; no file was accepted."
                                !documentPickerAvailable -> "Use the supported JavaScript portal build or the Android driver app."
                                else -> "Choose one PDF, JPEG, or PNG up to 10 MB. The server verifies and scans it."
                            },
                            color = TaxiColors.Ink500,
                        )
                    }
                }
                if (editable && documentUploadAvailable && documentPickerAvailable) {
                    ApplicantPrimaryButton(
                        if (document == null) "Choose document" else "Replace document",
                        onClick = onUploadDocument,
                    )
                }
                if (editable && document != null) {
                    OutlinedButton(
                        onClick = { onDeleteDocument(document.id) },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text("Delete document", color = TaxiColors.Danger600)
                    }
                }
            }
        }
    }
}

@Composable
private fun EvidenceChoices(
    title: String,
    choices: List<Pair<String, String>>,
    selectedId: String?,
    enabled: Boolean,
    onSelect: (String) -> Unit,
) {
    Text(title, style = MaterialTheme.typography.labelLarge)
    if (choices.isEmpty()) {
        Text("No matching account-owned evidence is available.", color = TaxiColors.Warning600)
    } else {
        choices.forEach { (id, label) ->
            Surface(
                modifier = Modifier.fillMaxWidth().clickable(enabled = enabled) { onSelect(id) },
                color = if (id == selectedId) TaxiColors.Accent100 else TaxiColors.Surface1,
                shape = RoundedCornerShape(TaxiRadii.Md),
                border = BorderStroke(1.dp, if (id == selectedId) TaxiColors.Accent500 else TaxiColors.StrokeSubtle),
            ) {
                Text(label, Modifier.padding(TaxiSpacing.Sm))
            }
        }
    }
}

@Composable
private fun ApplicantVehicleForm(
    locked: Boolean,
    onRegister: (VehicleRegistration) -> Unit,
) {
    var make by remember { mutableStateOf("") }
    var model by remember { mutableStateOf("") }
    var year by remember { mutableStateOf("") }
    var color by remember { mutableStateOf("") }
    var plate by remember { mutableStateOf("") }
    var taxiId by remember { mutableStateOf("") }
    var capacity by remember { mutableStateOf("") }
    val parsedYear = year.toIntOrNull()
    val parsedCapacity = capacity.toIntOrNull()
    ApplicantCard {
        Text("Register a vehicle for review", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text("Taxi category and service eligibility appear as city requirements when policy requires them.", color = TaxiColors.Ink500)
        OutlinedTextField(make, { make = it.take(80) }, Modifier.fillMaxWidth(), label = { Text("Make") }, enabled = !locked)
        OutlinedTextField(model, { model = it.take(80) }, Modifier.fillMaxWidth(), label = { Text("Model") }, enabled = !locked)
        OutlinedTextField(year, { year = it.filter(Char::isDigit).take(4) }, Modifier.fillMaxWidth(), label = { Text("Year") }, enabled = !locked)
        OutlinedTextField(color, { color = it.take(60) }, Modifier.fillMaxWidth(), label = { Text("Color") }, enabled = !locked)
        OutlinedTextField(plate, { plate = it.take(64) }, Modifier.fillMaxWidth(), label = { Text("Registration plate") }, enabled = !locked)
        OutlinedTextField(taxiId, { taxiId = it.take(64) }, Modifier.fillMaxWidth(), label = { Text("Taxi identifier (optional)") }, enabled = !locked)
        OutlinedTextField(capacity, { capacity = it.filter(Char::isDigit).take(2) }, Modifier.fillMaxWidth(), label = { Text("Passenger capacity (optional, 1–12)") }, enabled = !locked)
        ApplicantPrimaryButton(
            "Register vehicle",
            onClick = {
                onRegister(
                    VehicleRegistration(
                        make = make.trim(),
                        model = model.trim(),
                        year = requireNotNull(parsedYear),
                        color = color.trim(),
                        registrationNumber = plate.trim(),
                        taxiIdentifier = taxiId.trim().ifBlank { null },
                        passengerCapacity = parsedCapacity,
                    ),
                )
            },
            enabled = !locked && make.isNotBlank() && model.isNotBlank() && color.isNotBlank() && plate.isNotBlank() &&
                parsedYear in 1900..2100 && (capacity.isBlank() || parsedCapacity in 1..12),
        )
    }
}

@Composable
private fun ApplicationTimeline(status: String) {
    val steps = listOf("SUBMITTED", "UNDER_REVIEW", "ADDITIONAL_INFORMATION_REQUIRED", "APPROVED", "REJECTED")
    ApplicantCard {
        Text("Application timeline", fontWeight = FontWeight.Bold)
        steps.forEach { step ->
            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                Text(if (step == status) "●" else "○", color = if (step == status) TaxiColors.Accent600 else TaxiColors.Ink300)
                Text(step.toDisplayLabel(), color = if (step == status) TaxiColors.Navy900 else TaxiColors.Ink500,
                    fontWeight = if (step == status) FontWeight.Bold else FontWeight.Normal)
            }
        }
        if (status == "WITHDRAWN") Text("● Withdrawn", color = TaxiColors.Danger600, fontWeight = FontWeight.Bold)
    }
}

private val WITHDRAWABLE_STATUSES = setOf("NOT_STARTED", "SUBMITTED", "UNDER_REVIEW", "ADDITIONAL_INFORMATION_REQUIRED")
