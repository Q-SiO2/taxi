package org.example.taximobile.applicant.ui

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.intl.Locale
import androidx.compose.ui.text.style.TextDirection
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
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.example.taximobile.operations.ui.recruitmentLabel
import org.example.taximobile.operations.ui.recruitmentTextStyle
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

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
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
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

    HorizontalDivider(color = taxiColors.StrokeSubtle)
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically) {
        Column {
            Text(application.cityName.forLanguage(language), style = MaterialTheme.typography.headlineSmall,
                color = taxiColors.Navy900, fontWeight = FontWeight.Bold)
            Text(stringResource(Res.string.requirement_version_value, ltrIsolate(application.requirementVersion)),
                color = taxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
        }
        ApplicantStatus(application.status)
    }

    ApplicationTimeline(application.status)

    application.latestDecision?.let { decision ->
        ApplicantCard {
            Text(stringResource(Res.string.latest_reviewer_message), style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
            Text(decision.message, style = recruitmentTextStyle(decision.message))
            Text(stringResource(Res.string.web_app_reason, recruitmentLabel(decision.reasonCode)), color = taxiColors.Ink500,
                style = MaterialTheme.typography.bodySmall)
        }
    }
    application.authorization?.let { authorization ->
        ApplicantCard(selected = authorization.status == "ACTIVE") {
            CityAuthorizationSummary(authorization.status, authorization.validUntil)
            Text(stringResource(Res.string.authorization_services, authorization.serviceTypes.map { recruitmentLabel(it) }.joinToString(" · ")))
            if (!authorization.scheduledOffersEnabled) {
                Text(stringResource(Res.string.authorization_scheduled_disabled), color = taxiColors.Ink500)
            }
        }
    }

    Text(stringResource(Res.string.application_requirements), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
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
            stringResource(Res.string.web_req_save),
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
            color = if (application.complete) taxiColors.Success100 else taxiColors.Warning100,
            shape = RoundedCornerShape(taxiRadii.Md),
        ) {
            Text(
                if (application.complete) stringResource(Res.string.application_complete)
                else stringResource(Res.string.application_incomplete),
                Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                color = if (application.complete) taxiColors.Success600 else taxiColors.Warning600,
            )
        }
        ApplicantPrimaryButton(
            stringResource(Res.string.submit_city_application),
            onClick = { onSubmit(application.id) },
            enabled = application.complete && !locked,
        )
    }

    if (application.status in WITHDRAWABLE_STATUSES) {
        OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { confirmWithdrawal = true }, enabled = !locked, modifier = Modifier.fillMaxWidth()) {
            Text(stringResource(Res.string.withdraw_application), color = taxiColors.Danger600)
        }
    }
    if (confirmWithdrawal) {
        ApplicantCard {
            Text(stringResource(Res.string.withdraw_application_title), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(stringResource(Res.string.withdraw_application_body))
            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { confirmWithdrawal = false }) { Text(stringResource(Res.string.web_app_keep)) }
                OutlinedButton(
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                    onClick = {
                        confirmWithdrawal = false
                        onWithdraw(application.id)
                    },
                    enabled = !locked,
                ) { Text(stringResource(Res.string.web_app_confirm_withdraw), color = taxiColors.Danger600) }
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
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    val language = Locale.current.language
    ApplicantCard(selected = missing) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            val label = requirement.label.forLanguage(language)
            Text(label, Modifier.weight(1f), fontWeight = FontWeight.Bold, style = recruitmentTextStyle(label))
            Text(if (missing) stringResource(Res.string.missing_requirement) else if (requirement.required) stringResource(Res.string.required_requirement) else stringResource(Res.string.optional_requirement),
                color = if (missing) taxiColors.Warning600 else taxiColors.Ink500,
                style = MaterialTheme.typography.labelMedium)
        }
        val description = requirement.description.forLanguage(language)
        Text(description, color = taxiColors.Ink500, style = recruitmentTextStyle(description))
        when (requirement.evidenceType) {
            DriverRequirementEvidenceType.PROFILE -> Text(stringResource(Res.string.profile_evidence_confirmed), color = taxiColors.Success600)
            DriverRequirementEvidenceType.BOOLEAN -> Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(booleanValue, onCheckedChange = onBoolean, enabled = editable)
                Text(stringResource(Res.string.boolean_requirement_confirmation))
            }
            DriverRequirementEvidenceType.DATE -> OutlinedTextField(
                textValue,
                { onText(it.take(10)) },
                Modifier.fillMaxWidth(),
                label = { Text(stringResource(Res.string.date_requirement_answer)) },
                singleLine = true,
                enabled = editable,
                textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr),
            )
            DriverRequirementEvidenceType.TEXT -> OutlinedTextField(
                textValue,
                { onText(it.take(1000)) },
                Modifier.fillMaxWidth(),
                label = { Text(stringResource(Res.string.text_requirement_answer)) },
                enabled = editable,
                textStyle = recruitmentTextStyle(textValue),
            )
            DriverRequirementEvidenceType.VEHICLE -> EvidenceChoices(
                stringResource(Res.string.select_evidence_vehicle),
                vehicles.map { it.id to "${it.make} ${it.model} · ${recruitmentLabel(it.verificationStatus)}" },
                selectedVehicleId,
                editable,
                onVehicle,
            )
            DriverRequirementEvidenceType.CREDENTIAL -> EvidenceChoices(
                stringResource(Res.string.select_evidence_credential),
                credentials.map { it.id to stringResource(Res.string.credential_summary, ltrIsolate(it.type), recruitmentLabel(it.status)) },
                selectedCredentialId,
                editable,
                onCredential,
            )
            DriverRequirementEvidenceType.DOCUMENT -> {
                Surface(
                    color = if (document == null) taxiColors.Warning100 else taxiColors.Success100,
                    shape = RoundedCornerShape(taxiRadii.Md),
                    border = BorderStroke(
                        1.dp,
                        if (document == null) taxiColors.Warning600.copy(alpha = 0.25f)
                        else taxiColors.Success600.copy(alpha = 0.25f),
                    ),
                ) {
                    Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md)) {
                        Text(
                            when {
                                document != null -> stringResource(Res.string.web_app_document_status, recruitmentLabel(document.scanStatus))
                                documentUploadAvailable && documentPickerAvailable -> stringResource(Res.string.document_status_ready)
                                else -> stringResource(Res.string.document_status_unavailable)
                            },
                            fontWeight = FontWeight.Bold,
                            color = if (document == null) taxiColors.Warning600 else taxiColors.Success600,
                        )
                        Text(
                            when {
                                document != null -> stringResource(Res.string.web_recruit_document_size, ltrIsolate(document.mediaType), ltrIsolate(document.byteSize.toString()))
                                !documentUploadAvailable -> stringResource(Res.string.web_app_upload_unavailable)
                                !documentPickerAvailable -> stringResource(Res.string.web_app_upload_client)
                                else -> stringResource(Res.string.web_app_upload_help)
                            },
                            color = taxiColors.Ink500,
                        )
                    }
                }
                if (editable && documentUploadAvailable && documentPickerAvailable) {
                    ApplicantPrimaryButton(
                        if (document == null) stringResource(Res.string.choose_document) else stringResource(Res.string.replace_document),
                        onClick = onUploadDocument,
                    )
                }
                if (editable && document != null) {
                    OutlinedButton(
                        shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                        onClick = { onDeleteDocument(document.id) },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text(stringResource(Res.string.delete_document), color = taxiColors.Danger600)
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
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Text(title, style = MaterialTheme.typography.labelLarge)
    if (choices.isEmpty()) {
        Text(stringResource(Res.string.no_eligible_evidence), color = taxiColors.Warning600)
    } else {
        choices.forEach { (id, label) ->
            Surface(
                modifier = Modifier.fillMaxWidth().clickable(enabled = enabled) { onSelect(id) },
                color = if (id == selectedId) taxiColors.Accent100 else taxiColors.Surface1,
                shape = RoundedCornerShape(taxiRadii.Md),
                border = BorderStroke(1.dp, if (id == selectedId) taxiColors.Accent500 else taxiColors.StrokeSubtle),
            ) {
                Text(label, Modifier.padding(TaxiSpacing.Sm), style = recruitmentTextStyle(label))
            }
        }
    }
}

@Composable
private fun ApplicantVehicleForm(
    locked: Boolean,
    onRegister: (VehicleRegistration) -> Unit,
) {
    val taxiColors = TaxiTheme.colors
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
        Text(stringResource(Res.string.register_required_vehicle), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text(stringResource(Res.string.city_controls_vehicle_eligibility), color = taxiColors.Ink500)
        OutlinedTextField(make, { make = it.take(80) }, Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.vehicle_make)) }, enabled = !locked, textStyle = recruitmentTextStyle(make))
        OutlinedTextField(model, { model = it.take(80) }, Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.vehicle_model)) }, enabled = !locked, textStyle = recruitmentTextStyle(model))
        OutlinedTextField(year, { year = it.filter(Char::isDigit).take(4) }, Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.vehicle_year)) }, enabled = !locked, textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr))
        OutlinedTextField(color, { color = it.take(60) }, Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.vehicle_color)) }, enabled = !locked, textStyle = recruitmentTextStyle(color))
        OutlinedTextField(plate, { plate = it.take(64) }, Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.registration_number)) }, enabled = !locked, textStyle = recruitmentTextStyle(plate).copy(textDirection = TextDirection.Ltr))
        OutlinedTextField(taxiId, { taxiId = it.take(64) }, Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.taxi_identifier_optional)) }, enabled = !locked, textStyle = recruitmentTextStyle(taxiId).copy(textDirection = TextDirection.Ltr))
        OutlinedTextField(capacity, { capacity = it.filter(Char::isDigit).take(2) }, Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.passenger_capacity_optional)) }, enabled = !locked, textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr))
        ApplicantPrimaryButton(
            stringResource(Res.string.register_vehicle),
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
    val taxiColors = TaxiTheme.colors
    val steps = listOf("SUBMITTED", "UNDER_REVIEW", "ADDITIONAL_INFORMATION_REQUIRED", "APPROVED", "REJECTED")
    ApplicantCard {
        Text(stringResource(Res.string.application_timeline), fontWeight = FontWeight.Bold)
        steps.forEach { step ->
            val current = step == status
            Row(
                modifier = Modifier.semantics(mergeDescendants = true) { selected = current },
                horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Canvas(Modifier.size(12.dp)) {
                    val markerColor = if (current) taxiColors.Accent600 else taxiColors.Ink300
                    if (current) {
                        drawCircle(markerColor, radius = 4.dp.toPx())
                    } else {
                        drawCircle(markerColor, radius = 4.dp.toPx(), style = Stroke(1.5.dp.toPx()))
                    }
                }
                Text(recruitmentLabel(step), color = if (step == status) taxiColors.Navy900 else taxiColors.Ink500,
                    fontWeight = if (step == status) FontWeight.Bold else FontWeight.Normal)
            }
        }
        if (status == "WITHDRAWN") Text(stringResource(Res.string.application_status_withdrawn), color = taxiColors.Danger600, fontWeight = FontWeight.Bold)
    }
}

private val WITHDRAWABLE_STATUSES = setOf("NOT_STARTED", "SUBMITTED", "UNDER_REVIEW", "ADDITIONAL_INFORMATION_REQUIRED")
