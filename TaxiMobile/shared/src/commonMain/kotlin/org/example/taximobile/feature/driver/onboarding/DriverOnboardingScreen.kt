package org.example.taximobile.feature.driver.onboarding

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.intl.Locale
import androidx.compose.ui.unit.dp
import org.example.taximobile.domain.drivers.DriverApplicationAnswerDraft
import org.example.taximobile.domain.drivers.DriverApplicationEvidenceDraft
import org.example.taximobile.domain.drivers.DriverCityApplication
import org.example.taximobile.domain.drivers.DriverRequirement
import org.example.taximobile.domain.drivers.DriverRequirementEvidenceType
import org.example.taximobile.domain.drivers.VehicleRegistration
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.feature.app.driverApplicationStatusResource
import org.example.taximobile.feature.app.isPending
import org.example.taximobile.feature.ui.components.ConfirmDialog
import org.example.taximobile.feature.ui.components.DriverDocumentCard
import org.example.taximobile.feature.ui.components.StatusPill
import org.example.taximobile.feature.ui.components.StatusTone
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiButtonStyle
import org.example.taximobile.feature.ui.components.TaxiCard
import org.example.taximobile.feature.ui.components.TaxiTextField
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.text.resolve
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
fun DriverOnboardingScreen(
    state: AppUiState.DriverOnboarding,
    pendingAction: AppAction?,
    onRefresh: () -> Unit,
    onLogout: () -> Unit,
    onCreateApplication: (cityId: String, displayName: String) -> Unit,
    onSelectApplication: (applicationId: String, displayName: String) -> Unit,
    onSaveApplication: (
        applicationId: String,
        expectedVersion: Int,
        displayName: String,
        answers: List<DriverApplicationAnswerDraft>,
        evidence: List<DriverApplicationEvidenceDraft>,
        removeAnswerItemIds: List<String>,
        removeEvidenceItemIds: List<String>,
    ) -> Unit,
    onSubmitApplication: (applicationId: String, displayName: String) -> Unit,
    onWithdrawApplication: (applicationId: String, displayName: String) -> Unit,
    documentPickerAvailable: Boolean,
    onUploadDocument: (String, String, Int, String) -> Unit,
    onDeleteDocument: (String, String, Int, String) -> Unit,
    onRegisterVehicle: (displayName: String, VehicleRegistration) -> Unit,
) {
    val language = Locale.current.language
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(TaxiSpacing.Lg),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg),
    ) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    stringResource(Res.string.driver_onboarding_title),
                    style = MaterialTheme.typography.headlineSmall,
                    color = TaxiColors.Navy900,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    state.displayName,
                    style = MaterialTheme.typography.bodyMedium,
                    color = TaxiColors.Ink500,
                )
            }
            TaxiButton(
                label = stringResource(Res.string.sign_out),
                onClick = onLogout,
                style = TaxiButtonStyle.Secondary,
                modifier = Modifier.fillMaxWidth(0.35f),
            )
        }

        state.message?.let { message ->
            Surface(
                color = TaxiColors.Danger100,
                shape = RoundedCornerShape(TaxiRadii.Md),
                border = BorderStroke(1.dp, TaxiColors.Danger600.copy(alpha = 0.25f)),
            ) {
                Text(
                    message.resolve(),
                    Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                    color = TaxiColors.Danger600,
                )
            }
        }

        TaxiCard {
            Text(stringResource(Res.string.driver_onboarding_intro), style = MaterialTheme.typography.bodyLarge)
            Text(
                stringResource(Res.string.driver_onboarding_workflow),
                style = MaterialTheme.typography.bodyMedium,
                color = TaxiColors.Ink500,
            )
        }

        if (state.applications.isNotEmpty()) {
            Text(
                stringResource(Res.string.driver_city_applications),
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )
            state.applications.forEach { application ->
                val selected = application.id == state.selectedApplication?.id
                TaxiCard(
                    selected = selected,
                    modifier = Modifier.clickable(
                        enabled = pendingAction == null && !selected,
                    ) { onSelectApplication(application.id, state.displayName) },
                ) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(
                            application.cityName.forLanguage(language),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                        )
                        StatusPill(
                            stringResource(driverApplicationStatusResource(application.status)),
                            application.status.statusTone(),
                        )
                    }
                    Text(
                        stringResource(Res.string.requirement_version_value, application.requirementVersion),
                        color = TaxiColors.Ink500,
                        style = MaterialTheme.typography.bodySmall,
                    )
                    application.latestApplicantMessage?.let {
                        Text(it, color = TaxiColors.Navy700, style = MaterialTheme.typography.bodyMedium)
                    }
                    if (!selected) {
                        Text(
                            stringResource(Res.string.continue_application),
                            color = TaxiColors.Navy700,
                            style = MaterialTheme.typography.labelLarge,
                        )
                    }
                }
            }
        }

        state.selectedApplication?.let { application ->
            ApplicationDetail(
                application = application,
                displayName = state.displayName,
                vehicles = state.vehicles,
                credentials = state.credentials,
                language = language,
                pendingAction = pendingAction,
                onSave = onSaveApplication,
                onSubmit = onSubmitApplication,
                onWithdraw = onWithdrawApplication,
                documentPickerAvailable = documentPickerAvailable,
                onUploadDocument = onUploadDocument,
                onDeleteDocument = onDeleteDocument,
                onRegisterVehicle = onRegisterVehicle,
            )
        }

        RecruitingCities(
            state = state,
            language = language,
            pendingAction = pendingAction,
            onCreateApplication = onCreateApplication,
            onSelectApplication = onSelectApplication,
        )

        TaxiButton(
            stringResource(Res.string.refresh_application),
            onRefresh,
            style = TaxiButtonStyle.Secondary,
            loading = pendingAction.isPending(AppActionKind.REFRESH),
        )
        Spacer(Modifier.height(TaxiSpacing.Xl))
    }
}

@Composable
private fun RecruitingCities(
    state: AppUiState.DriverOnboarding,
    language: String,
    pendingAction: AppAction?,
    onCreateApplication: (String, String) -> Unit,
    onSelectApplication: (String, String) -> Unit,
) {
    Text(
        stringResource(Res.string.recruiting_cities),
        style = MaterialTheme.typography.titleLarge,
        fontWeight = FontWeight.Bold,
    )
    if (state.recruitingCities.isEmpty()) {
        TaxiCard { Text(stringResource(Res.string.no_recruiting_cities), color = TaxiColors.Ink500) }
        return
    }
    state.recruitingCities.forEach { city ->
        val openApplication = state.applications.firstOrNull {
            it.cityId == city.id && it.status in OPEN_APPLICATION_STATUSES
        }
        TaxiCard {
            Text(
                city.name.forLanguage(language),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(
                stringResource(Res.string.requirement_version_value, city.requirementVersion),
                color = TaxiColors.Ink500,
                style = MaterialTheme.typography.bodySmall,
            )
            TaxiButton(
                label = stringResource(
                    if (openApplication == null) Res.string.start_city_application
                    else Res.string.continue_application,
                ),
                onClick = {
                    if (openApplication == null) {
                        onCreateApplication(city.id, state.displayName)
                    } else {
                        onSelectApplication(openApplication.id, state.displayName)
                    }
                },
                enabled = pendingAction == null,
                loading = pendingAction.isPending(
                    if (openApplication == null) AppActionKind.CREATE_DRIVER_CITY_APPLICATION
                    else AppActionKind.SELECT_DRIVER_CITY_APPLICATION,
                    openApplication?.id ?: city.id,
                ),
            )
        }
    }
}

@Composable
private fun ApplicationDetail(
    application: DriverCityApplication,
    displayName: String,
    vehicles: List<org.example.taximobile.domain.drivers.DriverVehicle>,
    credentials: List<org.example.taximobile.domain.drivers.DriverCredential>,
    language: String,
    pendingAction: AppAction?,
    onSave: (
        String,
        Int,
        String,
        List<DriverApplicationAnswerDraft>,
        List<DriverApplicationEvidenceDraft>,
        List<String>,
        List<String>,
    ) -> Unit,
    onSubmit: (String, String) -> Unit,
    onWithdraw: (String, String) -> Unit,
    documentPickerAvailable: Boolean,
    onUploadDocument: (String, String, Int, String) -> Unit,
    onDeleteDocument: (String, String, Int, String) -> Unit,
    onRegisterVehicle: (String, VehicleRegistration) -> Unit,
) {
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
            application.evidence.forEach { item -> item.vehicleId?.let { put(item.requirementItemId, it) } }
        }
    }
    val selectedCredentials = remember(draftKey) {
        mutableStateMapOf<String, String>().apply {
            application.evidence.forEach { item -> item.credentialId?.let { put(item.requirementItemId, it) } }
        }
    }
    var confirmWithdrawal by remember(application.id) { mutableStateOf(false) }

    HorizontalDivider(color = TaxiColors.StrokeSubtle)
    Text(
        application.cityName.forLanguage(language),
        style = MaterialTheme.typography.headlineSmall,
        color = TaxiColors.Navy900,
        fontWeight = FontWeight.Bold,
    )
    StatusPill(
        stringResource(driverApplicationStatusResource(application.status)),
        application.status.statusTone(),
    )
    Text(
        stringResource(
            Res.string.city_scoped_approval_notice,
            application.cityName.forLanguage(language),
        ),
        color = TaxiColors.Navy700,
        style = MaterialTheme.typography.bodyMedium,
    )

    ApplicationTimeline(application.status)

    application.latestDecision?.let { decision ->
        TaxiCard {
            Text(
                stringResource(Res.string.latest_reviewer_message),
                style = MaterialTheme.typography.titleSmall,
            )
            Text(decision.message, style = MaterialTheme.typography.bodyLarge)
        }
    }

    application.authorization?.let { authorization ->
        TaxiCard(selected = authorization.status == "ACTIVE") {
            CityAuthorizationSummary(authorization.status, authorization.validUntil)
            Text(stringResource(Res.string.authorization_services, authorization.serviceTypes.joinToString()))
            if (!authorization.scheduledOffersEnabled) {
                Text(
                    stringResource(Res.string.authorization_scheduled_disabled),
                    color = TaxiColors.Ink500,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }

    if (application.editable) {
        TaxiCard {
            Text(stringResource(Res.string.identity_details), style = MaterialTheme.typography.titleMedium)
            TaxiTextField(
                value = displayName,
                onValueChange = {},
                label = stringResource(Res.string.driver_display_name),
                readOnly = true,
            )
            Text(
                stringResource(Res.string.identity_details_help),
                style = MaterialTheme.typography.bodySmall,
                color = TaxiColors.Ink500,
            )
        }
    }

    Text(
        stringResource(Res.string.application_requirements),
        style = MaterialTheme.typography.titleLarge,
        fontWeight = FontWeight.Bold,
    )
    application.requirements.sortedBy { it.displayOrder }.forEach { requirement ->
        RequirementEditor(
            requirement = requirement,
            editable = application.editable,
            missing = requirement.id in application.missingRequiredItemIds,
            language = language,
            textValue = textValues[requirement.id].orEmpty(),
            booleanValue = booleanValues[requirement.id] ?: false,
            selectedVehicleId = selectedVehicles[requirement.id],
            selectedCredentialId = selectedCredentials[requirement.id],
            vehicles = vehicles,
            credentials = credentials.filter {
                requirement.referenceType == null || requirement.referenceType == it.type
            },
            documentUploadAvailable = application.documentUploadAvailable,
            documentPickerAvailable = documentPickerAvailable,
            document = application.documents.firstOrNull {
                it.requirementItemId == requirement.id
            },
            documentMutationPending = pendingAction?.kind in setOf(
                AppActionKind.UPLOAD_DRIVER_APPLICATION_DOCUMENT,
                AppActionKind.DELETE_DRIVER_APPLICATION_DOCUMENT,
            ),
            onUploadDocument = {
                onUploadDocument(
                    application.id,
                    requirement.id,
                    application.optimisticVersion,
                    displayName,
                )
            },
            onDeleteDocument = { documentId ->
                onDeleteDocument(
                    application.id,
                    documentId,
                    application.optimisticVersion,
                    displayName,
                )
            },
            onText = { textValues[requirement.id] = it },
            onBoolean = { booleanValues[requirement.id] = it },
            onVehicle = {
                if (selectedVehicles[requirement.id] == it) selectedVehicles.remove(requirement.id)
                else selectedVehicles[requirement.id] = it
            },
            onCredential = {
                if (selectedCredentials[requirement.id] == it) selectedCredentials.remove(requirement.id)
                else selectedCredentials[requirement.id] = it
            },
        )
    }

    if (
        application.editable &&
        application.requirements.any { it.evidenceType == DriverRequirementEvidenceType.VEHICLE }
    ) {
        ApplicantVehicleForm(
            displayName = displayName,
            loading = pendingAction.isPending(AppActionKind.REGISTER_APPLICANT_VEHICLE),
            onRegister = onRegisterVehicle,
        )
    }

    if (application.editable) {
        val answers = application.requirements.mapNotNull { requirement ->
            when (requirement.evidenceType) {
                DriverRequirementEvidenceType.BOOLEAN -> DriverApplicationAnswerDraft(
                    requirementItemId = requirement.id,
                    answerType = "BOOLEAN",
                    booleanValue = booleanValues[requirement.id] ?: false,
                )
                DriverRequirementEvidenceType.DATE -> textValues[requirement.id]
                    ?.trim()
                    ?.takeIf(String::isNotEmpty)
                    ?.let { DriverApplicationAnswerDraft(requirement.id, "DATE", dateValue = it) }
                DriverRequirementEvidenceType.TEXT -> textValues[requirement.id]
                    ?.trim()
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
        val suppliedAnswerItemIds = answers.mapTo(mutableSetOf()) { it.requirementItemId }
        val removeAnswerItemIds = application.answers
            .map { it.requirementItemId }
            .filter { itemId ->
                itemId !in suppliedAnswerItemIds && application.requirements.any {
                    it.id == itemId && it.evidenceType in setOf(
                        DriverRequirementEvidenceType.DATE,
                        DriverRequirementEvidenceType.TEXT,
                    )
                }
            }
        val suppliedEvidenceItemIds = evidence.mapTo(mutableSetOf()) { it.requirementItemId }
        val removeEvidenceItemIds = application.evidence
            .map { it.requirementItemId }
            .filter { itemId ->
                itemId !in suppliedEvidenceItemIds && application.requirements.any {
                    it.id == itemId && it.evidenceType in setOf(
                        DriverRequirementEvidenceType.VEHICLE,
                        DriverRequirementEvidenceType.CREDENTIAL,
                    )
                }
            }
        TaxiButton(
            stringResource(Res.string.save_application),
            onClick = {
                onSave(
                    application.id,
                    application.optimisticVersion,
                    displayName,
                    answers,
                    evidence,
                    removeAnswerItemIds,
                    removeEvidenceItemIds,
                )
            },
            enabled = answers.isNotEmpty() || evidence.isNotEmpty() ||
                removeAnswerItemIds.isNotEmpty() || removeEvidenceItemIds.isNotEmpty(),
            loading = pendingAction.isPending(AppActionKind.SAVE_DRIVER_CITY_APPLICATION, application.id),
        )
        Surface(
            color = if (application.complete) TaxiColors.Success100 else TaxiColors.Warning100,
            shape = RoundedCornerShape(TaxiRadii.Md),
        ) {
            Text(
                stringResource(
                    if (application.complete) Res.string.application_complete
                    else Res.string.application_incomplete,
                ),
                Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                color = if (application.complete) TaxiColors.Success600 else TaxiColors.Warning600,
            )
        }
        TaxiButton(
            stringResource(Res.string.submit_city_application),
            onClick = { onSubmit(application.id, displayName) },
            enabled = application.complete,
            loading = pendingAction.isPending(AppActionKind.SUBMIT_DRIVER_CITY_APPLICATION, application.id),
        )
    }

    if (application.status in WITHDRAWABLE_APPLICATION_STATUSES) {
        TaxiButton(
            stringResource(Res.string.withdraw_application),
            onClick = { confirmWithdrawal = true },
            style = TaxiButtonStyle.Destructive,
            loading = pendingAction.isPending(AppActionKind.WITHDRAW_DRIVER_CITY_APPLICATION, application.id),
        )
    }
    if (confirmWithdrawal) {
        ConfirmDialog(
            title = stringResource(Res.string.withdraw_application_title),
            body = stringResource(Res.string.withdraw_application_body),
            confirmLabel = stringResource(Res.string.withdraw_application),
            destructive = true,
            onConfirm = {
                confirmWithdrawal = false
                onWithdraw(application.id, displayName)
            },
            onCancel = { confirmWithdrawal = false },
        )
    }
}

@Composable
private fun RequirementEditor(
    requirement: DriverRequirement,
    editable: Boolean,
    missing: Boolean,
    language: String,
    textValue: String,
    booleanValue: Boolean,
    selectedVehicleId: String?,
    selectedCredentialId: String?,
    vehicles: List<org.example.taximobile.domain.drivers.DriverVehicle>,
    credentials: List<org.example.taximobile.domain.drivers.DriverCredential>,
    documentUploadAvailable: Boolean,
    documentPickerAvailable: Boolean,
    document: org.example.taximobile.domain.drivers.DriverApplicationDocument?,
    documentMutationPending: Boolean,
    onUploadDocument: () -> Unit,
    onDeleteDocument: (String) -> Unit,
    onText: (String) -> Unit,
    onBoolean: (Boolean) -> Unit,
    onVehicle: (String) -> Unit,
    onCredential: (String) -> Unit,
) {
    TaxiCard(selected = missing) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(
                requirement.label.forLanguage(language),
                Modifier.weight(1f),
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
            )
            StatusPill(
                stringResource(
                    if (missing) Res.string.missing_requirement
                    else if (requirement.required) Res.string.required_requirement
                    else Res.string.optional_requirement,
                ),
                if (missing) StatusTone.Warning else StatusTone.Neutral,
            )
        }
        Text(
            requirement.description.forLanguage(language),
            style = MaterialTheme.typography.bodyMedium,
            color = TaxiColors.Ink500,
        )
        when (requirement.evidenceType) {
            DriverRequirementEvidenceType.PROFILE -> Text(
                stringResource(Res.string.profile_evidence_confirmed),
                color = TaxiColors.Success600,
                style = MaterialTheme.typography.bodyMedium,
            )
            DriverRequirementEvidenceType.BOOLEAN -> Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked = booleanValue, onCheckedChange = onBoolean, enabled = editable)
                Text(stringResource(Res.string.boolean_requirement_confirmation))
            }
            DriverRequirementEvidenceType.DATE -> TaxiTextField(
                value = textValue,
                onValueChange = { if (it.length <= 10) onText(it) },
                label = stringResource(Res.string.date_requirement_answer),
                enabled = editable,
                keyboardType = KeyboardType.Number,
            )
            DriverRequirementEvidenceType.TEXT -> TaxiTextField(
                value = textValue,
                onValueChange = { if (it.length <= 1000) onText(it) },
                label = stringResource(Res.string.text_requirement_answer),
                enabled = editable,
            )
            DriverRequirementEvidenceType.VEHICLE -> EvidenceChoices(
                title = stringResource(Res.string.select_evidence_vehicle),
                choices = vehicles.map { it.id to "${it.make} ${it.model} · ${it.verificationStatus}" },
                selectedId = selectedVehicleId,
                enabled = editable,
                onSelect = onVehicle,
            )
            DriverRequirementEvidenceType.CREDENTIAL -> EvidenceChoices(
                title = stringResource(Res.string.select_evidence_credential),
                choices = credentials.map { it.id to "${it.type} · ${it.status}" },
                selectedId = selectedCredentialId,
                enabled = editable,
                onSelect = onCredential,
            )
            DriverRequirementEvidenceType.DOCUMENT -> {
                DriverDocumentCard(
                    title = stringResource(Res.string.document_uploads),
                    status = document?.scanStatus ?: stringResource(
                        if (documentUploadAvailable && documentPickerAvailable) {
                            Res.string.document_status_ready
                        } else {
                            Res.string.document_status_unavailable
                        },
                    ),
                    detail = when {
                        document != null -> stringResource(
                            Res.string.document_uploaded_detail,
                            document.mediaType,
                            document.byteSize,
                        )
                        !documentUploadAvailable -> stringResource(Res.string.document_upload_unavailable)
                        !documentPickerAvailable -> stringResource(
                            Res.string.document_upload_client_unavailable,
                        )
                        else -> stringResource(Res.string.document_upload_help)
                    },
                )
                if (editable && documentUploadAvailable && documentPickerAvailable) {
                    TaxiButton(
                        label = stringResource(
                            if (document == null) Res.string.choose_document
                            else Res.string.replace_document,
                        ),
                        onClick = onUploadDocument,
                        loading = documentMutationPending,
                    )
                }
                if (editable && document != null) {
                    TaxiButton(
                        label = stringResource(Res.string.delete_document),
                        onClick = { onDeleteDocument(document.id) },
                        style = TaxiButtonStyle.Destructive,
                        loading = documentMutationPending,
                    )
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
        Text(stringResource(Res.string.no_eligible_evidence), color = TaxiColors.Warning600)
    } else {
        choices.forEach { (id, label) ->
            Surface(
                modifier = Modifier.fillMaxWidth().clickable(enabled = enabled) { onSelect(id) },
                color = if (id == selectedId) TaxiColors.Accent100 else TaxiColors.Surface1,
                shape = RoundedCornerShape(TaxiRadii.Md),
                border = BorderStroke(1.dp, if (id == selectedId) TaxiColors.Accent500 else TaxiColors.StrokeSubtle),
            ) {
                Text(label, Modifier.padding(TaxiSpacing.Sm), style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
private fun ApplicantVehicleForm(
    displayName: String,
    loading: Boolean,
    onRegister: (String, VehicleRegistration) -> Unit,
) {
    var make by remember { mutableStateOf("") }
    var model by remember { mutableStateOf("") }
    var year by remember { mutableStateOf("") }
    var color by remember { mutableStateOf("") }
    var plate by remember { mutableStateOf("") }
    var taxiIdentifier by remember { mutableStateOf("") }
    var passengerCapacity by remember { mutableStateOf("") }
    val parsedYear = year.toIntOrNull()
    val parsedCapacity = passengerCapacity.toIntOrNull()
    TaxiCard {
        Text(stringResource(Res.string.register_required_vehicle), style = MaterialTheme.typography.titleMedium)
        TaxiTextField(make, { make = it.take(80) }, stringResource(Res.string.vehicle_make))
        TaxiTextField(model, { model = it.take(80) }, stringResource(Res.string.vehicle_model))
        TaxiTextField(
            year,
            { year = it.filter(Char::isDigit).take(4) },
            stringResource(Res.string.vehicle_year),
            keyboardType = KeyboardType.Number,
        )
        TaxiTextField(color, { color = it.take(60) }, stringResource(Res.string.vehicle_color))
        TaxiTextField(plate, { plate = it.take(64) }, stringResource(Res.string.registration_number))
        TaxiTextField(
            taxiIdentifier,
            { taxiIdentifier = it.take(64) },
            stringResource(Res.string.taxi_identifier_optional),
        )
        TaxiTextField(
            passengerCapacity,
            { passengerCapacity = it.filter(Char::isDigit).take(2) },
            stringResource(Res.string.passenger_capacity_optional),
            keyboardType = KeyboardType.Number,
        )
        Text(
            stringResource(Res.string.city_controls_vehicle_eligibility),
            style = MaterialTheme.typography.bodySmall,
            color = TaxiColors.Ink500,
        )
        TaxiButton(
            stringResource(Res.string.register_vehicle),
            onClick = {
                onRegister(
                    displayName,
                    VehicleRegistration(
                        make = make.trim(),
                        model = model.trim(),
                        year = parsedYear!!,
                        color = color.trim(),
                        registrationNumber = plate.trim(),
                        taxiIdentifier = taxiIdentifier.trim().ifBlank { null },
                        passengerCapacity = parsedCapacity,
                    ),
                )
            },
            enabled = make.isNotBlank() && model.isNotBlank() && color.isNotBlank() &&
                plate.isNotBlank() && parsedYear in 1900..2100 &&
                (passengerCapacity.isBlank() || parsedCapacity in 1..12),
            loading = loading,
        )
    }
}

@Composable
private fun ApplicationTimeline(status: String) {
    val steps = listOf(
        "SUBMITTED" to Res.string.verification_submitted,
        "UNDER_REVIEW" to Res.string.verification_under_review,
        "ADDITIONAL_INFORMATION_REQUIRED" to Res.string.verification_more_information,
        "APPROVED" to Res.string.verification_verified,
        "REJECTED" to Res.string.verification_rejected,
    )
    TaxiCard {
        Text(stringResource(Res.string.application_timeline), style = MaterialTheme.typography.titleSmall)
        steps.forEach { (code, label) ->
            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                Text(if (code == status) "●" else "○", color = if (code == status) TaxiColors.Accent600 else TaxiColors.Ink300)
                Text(
                    stringResource(label),
                    color = if (code == status) TaxiColors.Navy900 else TaxiColors.Ink500,
                    fontWeight = if (code == status) FontWeight.Bold else FontWeight.Normal,
                )
            }
        }
        if (status == "WITHDRAWN") {
            Text("● ${stringResource(Res.string.withdraw_application)}", color = TaxiColors.Danger600)
        }
    }
}

private fun String.statusTone(): StatusTone = when (this) {
    "APPROVED" -> StatusTone.Success
    "REJECTED", "WITHDRAWN", "SUSPENDED", "EXPIRED" -> StatusTone.Danger
    "ADDITIONAL_INFORMATION_REQUIRED" -> StatusTone.Warning
    else -> StatusTone.Info
}

private val OPEN_APPLICATION_STATUSES = setOf(
    "NOT_STARTED",
    "SUBMITTED",
    "UNDER_REVIEW",
    "ADDITIONAL_INFORMATION_REQUIRED",
)

private val WITHDRAWABLE_APPLICATION_STATUSES = OPEN_APPLICATION_STATUSES
