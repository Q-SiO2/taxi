package org.example.taximobile.operations.state

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.random.Random
import kotlin.time.Clock
import org.example.taximobile.operations.data.OperationsApiException
import org.example.taximobile.operations.data.OperationsGateway
import org.example.taximobile.operations.model.AccountSecurityAction
import org.example.taximobile.operations.model.AccountSecurityActionRequest
import org.example.taximobile.operations.model.AdministrativeGrantCreateRequest
import org.example.taximobile.operations.model.AdministrativeGrantChangeRequestRecord
import org.example.taximobile.operations.model.AdministrativeGrantDecisionRequest
import org.example.taximobile.operations.model.AdministrativeGrantRecord
import org.example.taximobile.operations.model.AdministrativeGrantRevocationRequest
import org.example.taximobile.operations.model.CityRecord
import org.example.taximobile.operations.model.CityConfigurationRecord
import org.example.taximobile.operations.model.CityConfigurationCreateRequest
import org.example.taximobile.operations.model.CityCreateRequest
import org.example.taximobile.operations.model.CaseAlertRecord
import org.example.taximobile.operations.model.DriverApplicationDecisionRequest
import org.example.taximobile.operations.model.CityAuthorizationAction
import org.example.taximobile.operations.model.CityAuthorizationDecisionRequest
import org.example.taximobile.operations.model.cityAuthorizationActions
import org.example.taximobile.operations.model.DriverRequirementVersionCreateRequest
import org.example.taximobile.operations.model.DriverRequirementVersionRecord
import org.example.taximobile.operations.model.DriverRequirementVersionUpdateRequest
import org.example.taximobile.operations.model.FixedRouteCreateRequest
import org.example.taximobile.operations.model.FixedRouteRecord
import org.example.taximobile.operations.model.FixedRouteVersionCreateRequest
import org.example.taximobile.operations.model.FixedRouteVersionRecord
import org.example.taximobile.operations.model.MANAGE_FIXED_ROUTES
import org.example.taximobile.operations.model.MANAGE_ACCOUNT_SECURITY
import org.example.taximobile.operations.model.MANAGE_DRIVER_REQUIREMENTS
import org.example.taximobile.operations.model.MANAGE_CITY_LIFECYCLE
import org.example.taximobile.operations.model.MANAGE_CITY_CONFIGURATION
import org.example.taximobile.operations.model.MANAGE_OPERATORS
import org.example.taximobile.operations.model.MANAGE_OPERATOR_ASSIGNMENTS
import org.example.taximobile.operations.model.MANAGE_SERVICE_AREAS
import org.example.taximobile.operations.model.MANAGE_CITY_TARIFFS
import org.example.taximobile.operations.model.MANAGE_OPERATOR_FEE_POLICIES
import org.example.taximobile.operations.model.MANAGE_PAYMENT_CAPABILITIES
import org.example.taximobile.operations.model.MANAGE_SCHEDULING_POLICY
import org.example.taximobile.operations.model.MANAGE_SAFETY_CASES
import org.example.taximobile.operations.model.MANAGE_SCOPED_STAFF_GRANTS
import org.example.taximobile.operations.model.MANAGE_SECURITY_INCIDENTS
import org.example.taximobile.operations.model.MANAGE_SUPPORT_CASES
import org.example.taximobile.operations.model.MANAGE_CASE_RETENTION
import org.example.taximobile.operations.model.LegalHoldCreateCommand
import org.example.taximobile.operations.model.LegalHoldRecord
import org.example.taximobile.operations.model.OperatorFeePolicyCreateRequest
import org.example.taximobile.operations.model.OperatorFeePolicyRecord
import org.example.taximobile.operations.model.OperatorFeePolicyUpdateRequest
import org.example.taximobile.operations.model.OperatorCityAssignment
import org.example.taximobile.operations.model.OperatorCityAssignmentCreateRequest
import org.example.taximobile.operations.model.OperatorCityAssignmentRetireRequest
import org.example.taximobile.operations.model.OperatorCreateRequest
import org.example.taximobile.operations.model.OperatorRecord
import org.example.taximobile.operations.model.OperatorStatusUpdateRequest
import org.example.taximobile.operations.model.OperationsDestination
import org.example.taximobile.operations.model.OperationsLoginResult
import org.example.taximobile.operations.model.OperationsScope
import org.example.taximobile.operations.model.OperationsSession
import org.example.taximobile.operations.model.OperationsSnapshot
import org.example.taximobile.operations.model.OperationsTokens
import org.example.taximobile.operations.model.PaymentCapabilityCreateRequest
import org.example.taximobile.operations.model.PaymentCapabilityRecord
import org.example.taximobile.operations.model.PaymentRecipientCreateRequest
import org.example.taximobile.operations.model.PaymentRecipientRecord
import org.example.taximobile.operations.model.PaymentRefundCreateRequest
import org.example.taximobile.operations.model.RECONCILE_PAYMENTS
import org.example.taximobile.operations.model.OperationsDriverApplicationDetail
import org.example.taximobile.operations.model.PricingRuleCreateRequest
import org.example.taximobile.operations.model.PricingRuleRecord
import org.example.taximobile.operations.model.PricingRuleUpdateRequest
import org.example.taximobile.operations.model.REVIEW_DRIVER_APPLICATIONS
import org.example.taximobile.operations.model.SchedulingPolicyCreateRequest
import org.example.taximobile.operations.model.SchedulingPolicyRecord
import org.example.taximobile.operations.model.SchedulingPolicyUpdateRequest
import org.example.taximobile.operations.model.ServiceAreaVersionCreateRequest
import org.example.taximobile.operations.model.ServiceAreaVersionRecord
import org.example.taximobile.operations.model.SafetyTransitionCommand
import org.example.taximobile.operations.model.SecurityIncidentCategory
import org.example.taximobile.operations.model.SecurityIncidentCreateRequest
import org.example.taximobile.operations.model.SecurityIncidentPostmortemCompleteRequest
import org.example.taximobile.operations.model.SecurityIncidentPostmortemOutcome
import org.example.taximobile.operations.model.SecurityIncidentRecord
import org.example.taximobile.operations.model.SecurityIncidentResponsibility
import org.example.taximobile.operations.model.SecurityIncidentResponsibilityAssignRequest
import org.example.taximobile.operations.model.SecurityIncidentResponsibilityRecord
import org.example.taximobile.operations.model.SecurityIncidentSeverity
import org.example.taximobile.operations.model.SecurityIncidentTimelineCreateRequest
import org.example.taximobile.operations.model.SecurityIncidentTimelineKind
import org.example.taximobile.operations.model.SecurityIncidentTimelineRecord
import org.example.taximobile.operations.model.SecurityIncidentTransition
import org.example.taximobile.operations.model.SecurityIncidentTransitionRequest
import org.example.taximobile.operations.model.SupportSafetyEscalationCommand
import org.example.taximobile.operations.model.SupportTransitionCommand
import org.example.taximobile.operations.model.SupportTriageCommand
import org.example.taximobile.operations.model.availableDestinations
import org.example.taximobile.operations.model.accountSecurityInputError
import org.example.taximobile.operations.model.administrativeGrantInputError
import org.example.taximobile.operations.model.administrativeGrantDecisionError
import org.example.taximobile.operations.model.configurationTargetFor
import org.example.taximobile.operations.model.normalizedScope
import org.example.taximobile.operations.model.matchesSelectedScope
import org.example.taximobile.operations.model.operatorStatusTargetsFor
import org.example.taximobile.operations.model.safetyTransitionTargets
import org.example.taximobile.operations.model.supportTransitionTargets
import org.example.taximobile.operations.model.serviceAreaTargetFor
import org.example.taximobile.operations.model.securityIncidentCreateInputError
import org.example.taximobile.operations.model.securityIncidentPostmortemInputError
import org.example.taximobile.operations.model.securityIncidentResponsibilityInputError
import org.example.taximobile.operations.model.securityIncidentTimelineInputError
import org.example.taximobile.operations.model.securityIncidentTransitionInputError

enum class OperationsSessionPhase {
    SIGNED_OUT,
    SIGNING_IN,
    MFA_REQUIRED,
    VERIFYING_MFA,
    SIGNED_IN,
}

data class OperationsMessage(
    val title: String,
    val detail: String,
)

data class OperationsUiState(
    val apiBaseUrl: String,
    val isLocalDevelopment: Boolean,
    val sessionPhase: OperationsSessionPhase = OperationsSessionPhase.SIGNED_OUT,
    val session: OperationsSession? = null,
    val authenticationStrength: String? = null,
    val mfaChallengeId: String? = null,
    val mfaChallengeExpiresIn: Int? = null,
    val mfaMethods: List<String> = emptyList(),
    val showMfaStepUp: Boolean = false,
    val destination: OperationsDestination = OperationsDestination.ROLLOUT,
    val scope: OperationsScope = OperationsScope(),
    val snapshot: OperationsSnapshot? = null,
    val selectedDriverApplication: OperationsDriverApplicationDetail? = null,
    val selectedSupportCase: org.example.taximobile.operations.model.SupportCaseDetail? = null,
    val selectedSafetyCase: org.example.taximobile.operations.model.SafetyCaseDetail? = null,
    val selectedSecurityIncident: SecurityIncidentRecord? = null,
    val securityIncidentTimeline: org.example.taximobile.operations.model.PagedResponse<SecurityIncidentTimelineRecord>? = null,
    val securityIncidentResponsibilities: org.example.taximobile.operations.model.PagedResponse<SecurityIncidentResponsibilityRecord>? = null,
    val isInitialLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val mutationLabel: String? = null,
    val error: OperationsMessage? = null,
    val notice: OperationsMessage? = null,
) {
    val destinations: List<OperationsDestination>
        get() = availableDestinations(session?.permissions.orEmpty())

    val interactionLocked: Boolean
        get() = isInitialLoading || isRefreshing || mutationLabel != null
}

class OperationsCoordinator(
    private val gateway: OperationsGateway,
    private val scope: CoroutineScope,
    apiBaseUrl: String,
    isLocalDevelopment: Boolean,
) {
    private val mutableState = MutableStateFlow(
        OperationsUiState(
            apiBaseUrl = apiBaseUrl,
            isLocalDevelopment = isLocalDevelopment,
        )
    )
    val state: StateFlow<OperationsUiState> = mutableState.asStateFlow()

    private var tokens: OperationsTokens? = null
    private var reloadJob: Job? = null

    fun login(identifier: String, password: String) {
        if (identifier.isBlank() || password.length < 8) {
            mutate {
                it.copy(
                    error = OperationsMessage(
                        title = "Check your credentials",
                        detail = "Enter an email or phone identifier and a password of at least 8 characters.",
                    )
                )
            }
            return
        }
        reloadJob?.cancel()
        reloadJob = scope.launch {
            mutate {
                it.copy(
                    sessionPhase = OperationsSessionPhase.SIGNING_IN,
                    isInitialLoading = true,
                    error = null,
                    notice = null,
                )
            }
            try {
                when (val result = gateway.login(identifier.trim(), password)) {
                    is OperationsLoginResult.MfaRequired -> mutate {
                        it.copy(
                            sessionPhase = OperationsSessionPhase.MFA_REQUIRED,
                            mfaChallengeId = result.challengeId,
                            mfaChallengeExpiresIn = result.expiresIn,
                            mfaMethods = result.methods,
                            isInitialLoading = false,
                        )
                    }
                    is OperationsLoginResult.Authenticated -> {
                        tokens = result.tokens
                        completeSignIn()
                    }
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                diagnoseLocalFailure("sign-in/load", error)
                tokens = null
                mutate {
                    it.copy(
                        sessionPhase = OperationsSessionPhase.SIGNED_OUT,
                        session = null,
                        snapshot = null,
                        isInitialLoading = false,
                        isRefreshing = false,
                        error = error.toMessage(signIn = true),
                    )
                }
            }
        }
    }

    fun verifyMfa(code: String) {
        val challengeId = mutableState.value.mfaChallengeId ?: return
        val normalized = code.trim()
        if (!normalized.matches(Regex("(?:[0-9]{6}|[A-Za-z0-9]{5}(?:-[A-Za-z0-9]{5}){3})"))) {
            mutate {
                it.copy(
                    error = OperationsMessage(
                        "Check the verification code",
                        "Enter a six-digit authenticator code or one complete recovery code.",
                    )
                )
            }
            return
        }
        reloadJob?.cancel()
        reloadJob = scope.launch {
            mutate {
                it.copy(
                    sessionPhase = OperationsSessionPhase.VERIFYING_MFA,
                    error = null,
                    notice = null,
                )
            }
            try {
                tokens = gateway.verifyMfa(challengeId, normalized)
                completeSignIn()
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                tokens = null
                mutate {
                    it.copy(
                        sessionPhase = OperationsSessionPhase.MFA_REQUIRED,
                        error = error.toMessage(signIn = true),
                    )
                }
            }
        }
    }

    fun cancelMfa() {
        reloadJob?.cancel()
        tokens = null
        mutate {
            it.copy(
                sessionPhase = OperationsSessionPhase.SIGNED_OUT,
                mfaChallengeId = null,
                mfaChallengeExpiresIn = null,
                mfaMethods = emptyList(),
                error = null,
            )
        }
    }

    private suspend fun completeSignIn() {
        val session = withAccessToken { gateway.session(it) }
        mutate {
            it.copy(
                sessionPhase = OperationsSessionPhase.SIGNED_IN,
                session = session,
                authenticationStrength = tokens?.authenticationStrength,
                mfaChallengeId = null,
                mfaChallengeExpiresIn = null,
                mfaMethods = emptyList(),
            )
        }
        reloadNow(OperationsScope(), initial = true)
    }

    fun showMfaStepUp() {
        if (mutableState.value.sessionPhase != OperationsSessionPhase.SIGNED_IN) return
        mutate { it.copy(showMfaStepUp = true, error = null) }
    }

    fun dismissMfaStepUp() {
        if (mutableState.value.mutationLabel == "Verifying MFA") return
        mutate { it.copy(showMfaStepUp = false) }
    }

    fun stepUpMfa(code: String) {
        val normalized = code.trim()
        if (normalized.length < 6 || mutableState.value.interactionLocked) return
        scope.launch {
            mutate { it.copy(mutationLabel = "Verifying MFA", error = null) }
            try {
                val result = withAccessToken { gateway.stepUpMfa(it, normalized) }
                val updatedSession = withAccessToken { gateway.session(it) }
                mutate {
                    it.copy(
                        session = updatedSession,
                        authenticationStrength = result.authenticationStrength,
                        showMfaStepUp = false,
                        mutationLabel = null,
                        notice = OperationsMessage(
                            "Sensitive actions unlocked",
                            "MFA was reverified. Step-up authorization is valid for ten minutes.",
                        ),
                    )
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                mutate { it.copy(mutationLabel = null, error = error.toMessage()) }
            }
        }
    }

    fun retry() {
        val current = mutableState.value
        if (current.sessionPhase != OperationsSessionPhase.SIGNED_IN) return
        reload(current.scope)
    }

    fun refresh() = retry()

    fun selectDestination(destination: OperationsDestination) {
        if (destination !in mutableState.value.destinations) return
        mutate { it.copy(destination = destination, error = null, notice = null) }
    }

    fun selectSupportCase(ticketId: String) {
        val current = mutableState.value
        val visible = current.snapshot?.caseOperations?.supportCases?.items
            ?.any { it.id == ticketId } == true
        if (
            current.session?.hasPermission(MANAGE_SUPPORT_CASES) != true ||
            !visible || current.interactionLocked
        ) return
        scope.launch {
            mutate { it.copy(mutationLabel = "Loading support case", error = null, notice = null) }
            try {
                val detail = withAccessToken { gateway.caseOperations.supportCase(it, ticketId) }
                mutate {
                    it.copy(
                        selectedSupportCase = detail,
                        selectedSafetyCase = null,
                        mutationLabel = null,
                    )
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleMutationFailure(error)
            }
        }
    }

    fun selectSafetyCase(reportId: String) {
        val current = mutableState.value
        val visible = current.snapshot?.caseOperations?.safetyCases?.items
            ?.any { it.id == reportId } == true
        if (
            current.session?.hasPermission(MANAGE_SAFETY_CASES) != true ||
            !visible || current.interactionLocked
        ) return
        scope.launch {
            mutate { it.copy(mutationLabel = "Loading safety case", error = null, notice = null) }
            try {
                val detail = withAccessToken { gateway.caseOperations.safetyCase(it, reportId) }
                mutate {
                    it.copy(
                        selectedSafetyCase = detail,
                        selectedSupportCase = null,
                        mutationLabel = null,
                    )
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleMutationFailure(error)
            }
        }
    }

    fun dismissSelectedCase() = mutate {
        it.copy(selectedSupportCase = null, selectedSafetyCase = null)
    }

    fun triageSupportCase(command: SupportTriageCommand) {
        val current = mutableState.value
        val selected = current.selectedSupportCase
        if (current.session?.hasPermission(MANAGE_SUPPORT_CASES) != true || selected == null) {
            fail("Support case required", "Select a support case inside your granted city scope.")
            return
        }
        if (
            command.priority !in setOf("LOW", "NORMAL", "HIGH", "URGENT") ||
            command.participantMessage.trim().length !in 3..1000 ||
            command.internalNote.trim().length !in 3..1000
        ) {
            fail(
                "Triage details required",
                "Choose a priority and provide separate participant and internal messages of 3 to 1,000 characters.",
            )
            return
        }
        launchMutation("Claiming support case ${selected.id.take(8)}") {
            val updated = withAccessToken {
                gateway.caseOperations.triageSupport(
                    it,
                    selected.id,
                    buildCaseIdempotencyKey("support-triage", selected.id),
                    command.copy(
                        participantMessage = command.participantMessage.trim(),
                        internalNote = command.internalNote.trim(),
                    ),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            mutate {
                it.copy(
                    selectedSupportCase = updated,
                    notice = OperationsMessage(
                        "Support case claimed",
                        "The participant acknowledgement was recorded and the case is ${updated.status}.",
                    ),
                )
            }
        }
    }

    fun transitionSupportCase(command: SupportTransitionCommand) {
        val current = mutableState.value
        val selected = current.selectedSupportCase
        if (current.session?.hasPermission(MANAGE_SUPPORT_CASES) != true || selected == null) {
            fail("Support case required", "Select a support case inside your granted city scope.")
            return
        }
        val terminal = command.targetStatus in setOf("RESOLVED", "CLOSED")
        if (
            command.targetStatus !in supportTransitionTargets(selected.status) ||
            command.internalNote.trim().length !in 3..1000 ||
            (terminal && command.participantMessage?.trim()?.length !in 3..1000) ||
            (terminal && command.resolutionCode.isNullOrBlank()) ||
            (!terminal && command.resolutionCode != null)
        ) {
            fail(
                "Support transition incomplete",
                "Use a documented next status, a controlled resolution code when required, and participant-safe/internal messages.",
            )
            return
        }
        launchMutation("Moving support case to ${command.targetStatus.lowercase()}") {
            val updated = withAccessToken {
                gateway.caseOperations.transitionSupport(
                    it,
                    selected.id,
                    buildCaseIdempotencyKey("support-transition", selected.id),
                    command.copy(
                        participantMessage = command.participantMessage?.trim(),
                        internalNote = command.internalNote.trim(),
                    ),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            mutate {
                it.copy(
                    selectedSupportCase = updated,
                    notice = OperationsMessage("Support case updated", "The case is now ${updated.status}."),
                )
            }
        }
    }

    fun escalateSupportCase(command: SupportSafetyEscalationCommand) {
        val current = mutableState.value
        val selected = current.selectedSupportCase
        val categories = setOf(
            "IMMEDIATE_DANGER", "ASSAULT", "HARASSMENT", "UNSAFE_DRIVING",
            "DISCRIMINATION", "VEHICLE_SAFETY", "OTHER_SAFETY",
        )
        if (current.session?.hasPermission(MANAGE_SUPPORT_CASES) != true || selected == null) {
            fail("Support case required", "Select a ride-linked support case inside your granted city scope.")
            return
        }
        if (selected.rideId == null || command.category !in categories || command.internalNote.trim().length !in 3..1000) {
            fail(
                "Safety handoff incomplete",
                "A ride-linked case, controlled safety category, and internal handoff note are required.",
            )
            return
        }
        launchMutation("Handing support case to safety") {
            val receipt = withAccessToken {
                gateway.caseOperations.escalateSupport(
                    it,
                    selected.id,
                    buildCaseIdempotencyKey("support-safety", selected.id),
                    command.copy(internalNote = command.internalNote.trim()),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice(
                "Safety handoff created",
                "Restricted safety report ${receipt.safetyReportId.take(8)} is ${receipt.status}. Safety details require a safety grant.",
            )
        }
    }

    fun transitionSafetyCase(command: SafetyTransitionCommand) {
        val current = mutableState.value
        val selected = current.selectedSafetyCase
        if (current.session?.hasPermission(MANAGE_SAFETY_CASES) != true || selected == null) {
            fail("Safety case required", "Select a safety case inside your granted city scope.")
            return
        }
        val terminal = command.targetStatus in setOf("RESOLVED", "CLOSED")
        if (
            command.targetStatus !in safetyTransitionTargets(selected.status) ||
            command.participantMessage.trim().length !in 3..1000 ||
            command.internalNote.trim().length !in 3..1000 ||
            (terminal && command.resolutionCode.isNullOrBlank()) ||
            (!terminal && command.resolutionCode != null)
        ) {
            fail(
                "Safety transition incomplete",
                "Use a documented next status, participant-safe message, internal note, and controlled resolution code when required.",
            )
            return
        }
        launchMutation("Moving safety case to ${command.targetStatus.lowercase()}") {
            val updated = withAccessToken {
                gateway.caseOperations.transitionSafety(
                    it,
                    selected.id,
                    buildCaseIdempotencyKey("safety-transition", selected.id),
                    command.copy(
                        participantMessage = command.participantMessage.trim(),
                        internalNote = command.internalNote.trim(),
                    ),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            mutate {
                it.copy(
                    selectedSafetyCase = updated,
                    notice = OperationsMessage("Safety case updated", "The case is now ${updated.status}."),
                )
            }
        }
    }

    fun acknowledgeCaseAlert(alert: CaseAlertRecord, reason: String) {
        val current = mutableState.value
        val permission = if (alert.caseType == "SUPPORT") MANAGE_SUPPORT_CASES else MANAGE_SAFETY_CASES
        val visible = current.snapshot?.caseOperations?.alerts?.items?.any { it.id == alert.id } == true
        if (current.session?.hasPermission(permission) != true || !visible) {
            fail("Overdue alert required", "Select an alert inside your granted queue and city scope.")
            return
        }
        if (reason.trim().length !in 3..240) {
            fail("Acknowledgement reason required", "Enter a bounded reason between 3 and 240 characters.")
            return
        }
        launchMutation("Acknowledging overdue ${alert.caseType.lowercase()} alert") {
            withAccessToken {
                gateway.caseOperations.acknowledgeAlert(
                    it,
                    alert.id,
                    buildCaseIdempotencyKey("case-alert", alert.id),
                    reason,
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Pager acknowledged", "Repeat paging stopped; case ownership and response remain required.")
        }
    }

    fun placeCaseLegalHold(command: LegalHoldCreateCommand) {
        val current = mutableState.value
        val selectedMatches = when (command.caseKind) {
            "SUPPORT" -> current.selectedSupportCase?.id == command.caseId
            "SAFETY" -> current.selectedSafetyCase?.id == command.caseId
            else -> false
        }
        val reference = command.authorityReference.trim()
        if (current.session?.hasPermission(MANAGE_CASE_RETENTION) != true || !selectedMatches) {
            fail("Retention authority required", "Select an authorized case with platform retention permission.")
            return
        }
        if (
            command.reasonCode !in setOf(
                "LITIGATION", "REGULATORY_REQUEST", "LAW_ENFORCEMENT_REQUEST",
                "DISPUTE_PRESERVATION", "OTHER_LEGAL_OBLIGATION",
            ) ||
            !Regex("^[A-Za-z0-9][A-Za-z0-9._:/-]{2,239}$").matches(reference) ||
            command.reviewDueAt.trim().length !in 20..40
        ) {
            fail(
                "Legal hold details required",
                "Choose a controlled reason, a non-secret authority reference, and a timezone-aware review timestamp.",
            )
            return
        }
        launchMutation("Placing ${command.caseKind.lowercase()} legal hold") {
            val hold = withAccessToken {
                gateway.caseOperations.placeLegalHold(
                    it,
                    buildCaseIdempotencyKey("case-hold", command.caseId),
                    command.copy(
                        authorityReference = reference,
                        reviewDueAt = command.reviewDueAt.trim(),
                    ),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice(
                "Legal hold active",
                "${hold.reasonCode.replace('_', ' ')} preserves ${hold.caseKind.lowercase()} ${hold.caseId.take(8)} until controlled release.",
            )
        }
    }

    fun releaseCaseLegalHold(hold: LegalHoldRecord, reasonCode: String) {
        val current = mutableState.value
        val visible = current.snapshot?.caseOperations?.legalHolds?.items
            ?.any { it.id == hold.id && it.status == "ACTIVE" } == true
        if (current.session?.hasPermission(MANAGE_CASE_RETENTION) != true || !visible) {
            fail("Active legal hold required", "Select an active hold inside your authorized city scope.")
            return
        }
        if (reasonCode !in setOf("OBLIGATION_ENDED", "REQUEST_WITHDRAWN", "SUPERSEDED", "PLACED_IN_ERROR")) {
            fail("Release reason required", "Choose a controlled legal-hold release reason.")
            return
        }
        launchMutation("Releasing legal hold ${hold.id.take(8)}") {
            withAccessToken {
                gateway.caseOperations.releaseLegalHold(
                    it,
                    hold.id,
                    buildCaseIdempotencyKey("case-hold-release", hold.id),
                    reasonCode,
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice(
                "Legal hold released",
                "The hold was released. Any already-due case remains queued for the next retention worker pass.",
            )
        }
    }

    fun selectMarket(marketId: String?) {
        val current = mutableState.value
        if (current.interactionLocked || current.scope.marketId == marketId) return
        reload(OperationsScope(marketId = marketId))
    }

    fun selectOperator(operatorId: String?) {
        val current = mutableState.value
        if (current.interactionLocked || current.scope.operatorId == operatorId) return
        reload(current.scope.copy(operatorId = operatorId))
    }

    fun selectCity(cityId: String?) {
        val current = mutableState.value
        if (current.interactionLocked || current.scope.cityId == cityId) return
        reload(current.scope.copy(cityId = cityId))
    }

    fun createAdministrativeGrant(request: AdministrativeGrantCreateRequest) {
        val current = mutableState.value
        val session = current.session
        if (session?.hasPermission(MANAGE_SCOPED_STAFF_GRANTS) != true) {
            fail("Staff grant permission required", "Your active grants do not authorize staff-access changes.")
            return
        }
        val inputError = administrativeGrantInputError(request, session.userId, Clock.System.now())
        if (inputError != null) {
            fail("Grant review incomplete", inputError)
            return
        }
        if (!request.matchesSelectedScope(current.scope)) {
            fail(
                "Exact grant scope required",
                "Select the market, operator, or city that will own this role before confirming the grant.",
            )
            return
        }
        launchMutation("Requesting ${request.roleTemplate.replace('_', ' ').lowercase()}") {
            val created = withAccessToken {
                gateway.staffAccess.requestGrant(
                    it,
                    buildGrantIdempotencyKey("create", request.userId),
                    request,
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice(
                "Staff grant request submitted",
                "${created.roleTemplate.replace('_', ' ')} for ${created.targetUserId.take(8)} is pending an independent administrator decision.",
            )
        }
    }

    fun revokeAdministrativeGrant(grant: AdministrativeGrantRecord, reason: String) {
        val current = mutableState.value
        val session = current.session
        val visible = current.snapshot?.grants?.items?.any {
            it.id == grant.id && it.revokedAt == null
        } == true
        if (session?.hasPermission(MANAGE_SCOPED_STAFF_GRANTS) != true || !visible) {
            fail("Active staff grant required", "Refresh and select an active grant visible to your authorized market.")
            return
        }
        if (grant.userId.equals(session.userId, ignoreCase = true)) {
            fail("Self-revocation blocked", "A different authorized administrator must change your access.")
            return
        }
        if (!grantBelongsToSelectedMarket(grant, current)) {
            fail("Grant outside selected market", "Select the market that owns this grant before revoking it.")
            return
        }
        if (reason.trim().length !in 3..240) {
            fail("Revocation reason required", "Enter an audit reason between 3 and 240 characters.")
            return
        }
        launchMutation("Requesting ${grant.roleTemplate.replace('_', ' ').lowercase()} revocation") {
            val requested = withAccessToken {
                gateway.staffAccess.requestRevocation(
                    it,
                    buildGrantIdempotencyKey("revoke", grant.id),
                    AdministrativeGrantRevocationRequest(grant.id, reason.trim()),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice(
                "Staff revocation requested",
                "${requested.roleTemplate.replace('_', ' ')} for ${requested.targetUserId.take(8)} remains active until an independent administrator approves request ${requested.id.take(8)}.",
            )
        }
    }

    fun decideAdministrativeGrantRequest(
        request: AdministrativeGrantChangeRequestRecord,
        decision: String,
        reason: String,
    ) {
        val current = mutableState.value
        val session = current.session
        val visible = current.snapshot?.grantRequests?.items?.any {
            it.id == request.id && it.status == "PENDING" &&
                it.optimisticVersion == request.optimisticVersion
        } == true
        if (session?.hasPermission(MANAGE_SCOPED_STAFF_GRANTS) != true || !visible) {
            fail(
                "Pending staff request required",
                "Refresh and select a pending request visible to your authorized market.",
            )
            return
        }
        val inputError = administrativeGrantDecisionError(
            request,
            session.userId,
            decision,
            reason,
        )
        if (inputError != null) {
            fail("Staff request decision blocked", inputError)
            return
        }
        launchMutation("${decision.replaceFirstChar { it.uppercase() }} staff request") {
            val decided = withAccessToken {
                gateway.staffAccess.decide(
                    accessToken = it,
                    idempotencyKey = buildGrantIdempotencyKey(decision, request.id),
                    requestId = request.id,
                    decision = decision,
                    request = AdministrativeGrantDecisionRequest(
                        expectedVersion = request.optimisticVersion,
                        reason = reason.trim(),
                    ),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice(
                "Staff request ${decided.status.lowercase()}",
                "Request ${decided.id.take(8)} is ${decided.status.lowercase()} at version ${decided.optimisticVersion}.",
            )
        }
    }

    fun createCity(request: CityCreateRequest) {
        val current = mutableState.value
        if (
            current.session?.hasPermission(MANAGE_CITY_LIFECYCLE) != true ||
            current.scope.marketId == null || current.scope.marketId != request.marketId
        ) {
            fail("Market scope required", "Select an authorized market before creating a city.")
            return
        }
        if (
            !request.code.matches(Regex("[a-z0-9]+(?:-[a-z0-9]+)*")) ||
            request.localizedName.en.isBlank() || request.localizedName.fr.isBlank() ||
            request.localizedName.ar.isBlank() || !request.timezone.contains('/')
        ) {
            fail("City details incomplete", "Provide a slug code, all three names, a region timezone, and valid coordinates.")
            return
        }
        launchMutation("Creating city ${request.code}") {
            val created = withAccessToken { gateway.controlPlane.createCity(it, request) }
            reloadNow(
                OperationsScope(marketId = created.marketId, cityId = created.id),
                initial = false,
            )
            notice("City created", "${created.localizedName.preferred()} is DRAFT and selected for configuration.")
        }
    }

    fun createOperator(request: OperatorCreateRequest) {
        val current = mutableState.value
        if (
            current.session?.hasPermission(MANAGE_OPERATORS) != true ||
            current.scope.marketId == null || current.scope.marketId != request.marketId
        ) {
            fail("Market scope required", "Select an authorized market with operator-management permission.")
            return
        }
        if (request.name.trim().isEmpty()) {
            fail("Operator name required", "Enter the legal or operating name before creating the operator.")
            return
        }
        launchMutation("Creating operator ${request.name}") {
            val created = withAccessToken { gateway.controlPlane.createOperator(it, request) }
            reloadNow(
                OperationsScope(marketId = created.marketId, operatorId = created.id),
                initial = false,
            )
            notice("Operator created", "${created.name} is ${created.status}; review and activate it before assignment.")
        }
    }

    fun updateOperatorStatus(operator: OperatorRecord, targetStatus: String) {
        val current = mutableState.value
        if (
            current.session?.hasPermission(MANAGE_OPERATORS) != true ||
            current.scope.marketId != operator.marketId ||
            targetStatus !in operatorStatusTargetsFor(operator.status)
        ) {
            fail("Operator command unavailable", "The operator is outside the active market or the transition is unsupported.")
            return
        }
        launchMutation("Changing operator ${operator.name} to $targetStatus") {
            val updated = withAccessToken {
                gateway.controlPlane.updateOperatorStatus(it, operator.id, OperatorStatusUpdateRequest(targetStatus))
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Operator updated", "${updated.name} is now ${updated.status}.")
        }
    }

    fun createOperatorAssignment(request: OperatorCityAssignmentCreateRequest) {
        val current = mutableState.value
        if (
            current.session?.hasPermission(MANAGE_OPERATOR_ASSIGNMENTS) != true ||
            current.scope.cityId != request.cityId || current.scope.operatorId != request.operatorId
        ) {
            fail("Exact assignment scope required", "Select the authorized city and operator before assigning a service.")
            return
        }
        launchMutation("Assigning ${request.serviceType.replace('_', ' ').lowercase()} service") {
            val created = withAccessToken { gateway.controlPlane.createAssignment(it, request) }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Service assignment created", "The backend activated ${created.serviceType} authority for the selected scope.")
        }
    }

    fun retireOperatorAssignment(assignment: OperatorCityAssignment, reason: String) {
        val current = mutableState.value
        if (
            current.session?.hasPermission(MANAGE_OPERATOR_ASSIGNMENTS) != true ||
            current.scope.cityId != assignment.cityId || current.scope.operatorId != assignment.operatorId ||
            reason.trim().length !in 3..240
        ) {
            fail("Retirement review required", "Select the exact assignment and provide an audit reason of 3–240 characters.")
            return
        }
        launchMutation("Retiring ${assignment.serviceType.replace('_', ' ').lowercase()} assignment") {
            val retired = withAccessToken {
                gateway.controlPlane.retireAssignment(
                    it, assignment.id, OperatorCityAssignmentRetireRequest(reason.trim())
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Assignment retired", "${retired.serviceType} authority is ${retired.status}; historical records are unchanged.")
        }
    }

    fun createServiceArea(request: ServiceAreaVersionCreateRequest) {
        val current = mutableState.value
        val cityId = current.scope.cityId
        if (current.session?.hasPermission(MANAGE_SERVICE_AREAS) != true || cityId == null) {
            fail("City scope required", "Select an authorized city with service-area permission.")
            return
        }
        if (request.boundary.coordinates.isEmpty()) {
            fail("Boundary required", "Provide at least one closed WGS84 polygon ring.")
            return
        }
        launchMutation("Creating service area ${request.version}") {
            val created = withAccessToken { gateway.controlPlane.createServiceArea(it, cityId, request) }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Service-area draft created", "${created.version} is DRAFT at backend version ${created.optimisticVersion}.")
        }
    }

    fun transitionServiceArea(area: ServiceAreaVersionRecord, targetStatus: String, reason: String) {
        val current = mutableState.value
        if (
            current.session?.hasPermission(MANAGE_SERVICE_AREAS) != true ||
            current.scope.cityId != area.cityId || serviceAreaTargetFor(area.status) != targetStatus ||
            reason.trim().length !in 3..240
        ) {
            fail("Service-area review invalid", "Refresh the city and provide a reason for the documented next transition.")
            return
        }
        launchMutation("Moving service area ${area.version} to $targetStatus") {
            val updated = withAccessToken {
                gateway.controlPlane.transitionServiceArea(it, area, targetStatus, reason)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Service-area status updated", "${updated.version} is now ${updated.status}.")
        }
    }

    fun createCityConfiguration(request: CityConfigurationCreateRequest) {
        val current = mutableState.value
        val cityId = current.scope.cityId
        if (current.session?.hasPermission(MANAGE_CITY_CONFIGURATION) != true || cityId == null) {
            fail("City configuration scope required", "Select an authorized city with configuration permission.")
            return
        }
        if (request.services.isEmpty() || request.services.map { it.serviceType }.distinct().size != request.services.size) {
            fail("Coherent service required", "Include one or more uniquely typed service assignments in the bundle.")
            return
        }
        launchMutation("Creating city configuration ${request.version}") {
            val created = withAccessToken { gateway.controlPlane.createConfiguration(it, cityId, request) }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Configuration draft created", "${created.version} is DRAFT; review each component before submission.")
        }
    }

    fun transitionCityConfiguration(
        configuration: CityConfigurationRecord,
        targetStatus: String,
        reason: String,
    ) {
        val current = mutableState.value
        if (
            current.session?.hasPermission(MANAGE_CITY_CONFIGURATION) != true ||
            current.scope.cityId != configuration.cityId || configurationTargetFor(configuration.status) != targetStatus ||
            reason.trim().length !in 3..240
        ) {
            fail("Configuration review invalid", "Refresh the bundle and provide a reason for its documented next transition.")
            return
        }
        launchMutation("Moving configuration ${configuration.version} to $targetStatus") {
            val updated = withAccessToken {
                gateway.controlPlane.transitionConfiguration(it, configuration, targetStatus, reason)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Configuration status updated", "${updated.version} is now ${updated.status}.")
        }
    }

    fun transitionCity(city: CityRecord, targetStatus: String, reason: String) {
        val current = mutableState.value
        if (current.session?.hasPermission(MANAGE_CITY_LIFECYCLE) != true) {
            mutate {
                it.copy(
                    error = OperationsMessage(
                        "Not authorized",
                        "Your active grants do not permit city lifecycle changes.",
                    )
                )
            }
            return
        }
        if (reason.trim().length < 3) {
            mutate {
                it.copy(
                    error = OperationsMessage(
                        "Reason required",
                        "Enter a review reason of at least 3 characters before confirming.",
                    )
                )
            }
            return
        }
        if (current.mutationLabel != null) return
        scope.launch {
            mutate {
                it.copy(
                    mutationLabel = "Changing ${city.localizedName.preferred()} to $targetStatus",
                    error = null,
                    notice = null,
                )
            }
            try {
                val updated = withAccessToken {
                    gateway.transitionCity(it, city, targetStatus, reason)
                }
                reloadNow(mutableState.value.scope, initial = false)
                mutate {
                    it.copy(
                        mutationLabel = null,
                        notice = OperationsMessage(
                            "Lifecycle updated",
                            "${updated.localizedName.preferred()} is now ${updated.lifecycleStatus} (version ${updated.optimisticVersion}).",
                        ),
                    )
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                diagnoseLocalFailure("city lifecycle", error)
                if (error is OperationsApiException && error.statusCode == 401) {
                    expireSession()
                } else {
                    // A conflict usually means another operator changed the
                    // version. Reload is explicit and never retries the command.
                    if (error is OperationsApiException && error.statusCode == 409) {
                        runCatching { reloadNow(mutableState.value.scope, initial = false) }
                    }
                    mutate {
                        it.copy(
                            mutationLabel = null,
                            isRefreshing = false,
                            error = error.toMessage(),
                        )
                    }
                }
            }
        }
    }

    fun decideCityReadiness(
        configuration: CityConfigurationRecord,
        gateCode: String,
        status: String,
        evidenceReference: String,
    ) {
        val current = mutableState.value
        if (current.session?.hasPermission(MANAGE_CITY_LIFECYCLE) != true) {
            fail("Not authorized", "Your active grants do not permit city readiness decisions.")
            return
        }
        if (status !in setOf("PASSED", "FAILED")) {
            fail("Decision required", "Choose PASSED or FAILED before confirming the review.")
            return
        }
        if (evidenceReference.trim().length < 3) {
            fail("Evidence reference required", "Enter a non-secret ticket, runbook, or review reference.")
            return
        }
        launchMutation("Recording ${gateCode.replace('_', ' ').lowercase()}") {
            val updated = withAccessToken {
                gateway.decideCityReadiness(
                    it,
                    configuration,
                    gateCode,
                    status,
                    evidenceReference,
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice(
                "Readiness decision recorded",
                "$gateCode is $status on ${updated.version} at backend version ${updated.optimisticVersion}.",
            )
        }
    }

    fun createDriverRequirementVersion(request: DriverRequirementVersionCreateRequest) {
        val current = mutableState.value
        val cityId = current.scope.cityId
        if (current.session?.hasPermission(MANAGE_DRIVER_REQUIREMENTS) != true || cityId == null) {
            fail("City requirement scope required", "Select an authorized city with requirement-management permission.")
            return
        }
        if (request.items.isEmpty()) {
            fail("Requirement item required", "A version must contain at least one explicit requirement item.")
            return
        }
        launchMutation("Creating driver requirement version ${request.version}") {
            val created = withAccessToken { gateway.createDriverRequirementVersion(it, cityId, request) }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Requirement draft created", "${created.version} is DRAFT at backend version ${created.optimisticVersion}.")
        }
    }

    fun updateDriverRequirementVersion(
        version: DriverRequirementVersionRecord,
        request: DriverRequirementVersionUpdateRequest,
    ) {
        val current = mutableState.value
        if (current.session?.hasPermission(MANAGE_DRIVER_REQUIREMENTS) != true || version.cityId != current.scope.cityId) {
            fail("Not authorized", "The selected requirement version is outside the active authorized city.")
            return
        }
        launchMutation("Updating driver requirement version ${version.version}") {
            val updated = withAccessToken { gateway.updateDriverRequirementVersion(it, version.id, request) }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Requirement draft saved", "The backend confirmed optimistic version ${updated.optimisticVersion}.")
        }
    }

    fun transitionDriverRequirementVersion(
        version: DriverRequirementVersionRecord,
        targetStatus: String,
        reason: String,
    ) {
        val current = mutableState.value
        if (current.session?.hasPermission(MANAGE_DRIVER_REQUIREMENTS) != true || version.cityId != current.scope.cityId) {
            fail("Not authorized", "The selected requirement version is outside the active authorized city.")
            return
        }
        if (reason.trim().length !in 3..240) {
            fail("Review reason required", "Enter a reason between 3 and 240 characters.")
            return
        }
        if (targetStatus !in setOf("IN_REVIEW", "ACTIVE")) {
            fail("Unsupported transition", "Refresh the version and choose a documented transition.")
            return
        }
        launchMutation("Moving requirement version ${version.version} to $targetStatus") {
            val updated = withAccessToken {
                gateway.transitionDriverRequirementVersion(it, version, targetStatus, reason)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Requirement status updated", "${updated.version} is now ${updated.status}.")
        }
    }

    fun createPricingRule(request: PricingRuleCreateRequest) {
        val cityId = pricingMutationScope(MANAGE_CITY_TARIFFS, request.operatorId) ?: return
        launchMutation("Creating tariff ${request.version}") {
            val created = withAccessToken {
                gateway.pricingEconomics.createPricingRule(it, cityId, request)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Tariff draft created", "${created.version} is DRAFT at backend version ${created.optimisticVersion}.")
        }
    }

    fun updatePricingRule(record: PricingRuleRecord, request: PricingRuleUpdateRequest) {
        if (!pricingRecordInScope(MANAGE_CITY_TARIFFS, record.cityId, record.operatorId)) return
        launchMutation("Updating tariff ${record.version}") {
            val updated = withAccessToken {
                gateway.pricingEconomics.updatePricingRule(it, record.id, request)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Tariff draft saved", "The backend confirmed revision ${updated.optimisticVersion}.")
        }
    }

    fun transitionPricingRule(record: PricingRuleRecord, target: String, reason: String) {
        if (!pricingRecordInScope(MANAGE_CITY_TARIFFS, record.cityId, record.operatorId)) return
        if (!validPolicyCommand(target, reason)) return
        launchMutation("Moving tariff ${record.version} to $target") {
            val updated = withAccessToken {
                gateway.pricingEconomics.transitionPricingRule(it, record, target, reason)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Tariff status updated", "${updated.version} is now ${updated.status}.")
        }
    }

    fun createPaymentRecipient(request: PaymentRecipientCreateRequest) {
        val cityId = paymentMutationScope(MANAGE_PAYMENT_CAPABILITIES, request.operatorId) ?: return
        launchMutation("Creating payment recipient ${request.label}") {
            val created = withAccessToken {
                gateway.paymentOperations.createRecipient(it, cityId, request)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Recipient draft created", "${created.label} must be independently verified before use.")
        }
    }

    fun transitionPaymentRecipient(record: PaymentRecipientRecord, target: String, reason: String) {
        if (!paymentRecordInScope(MANAGE_PAYMENT_CAPABILITIES, record.cityId, record.operatorId)) return
        if (target !in setOf("verify", "retire") || reason.trim().length !in 3..240) {
            fail("Valid reason required", "Choose verify or retire and enter an audited reason between 3 and 240 characters.")
            return
        }
        launchMutation("${target.replaceFirstChar { it.uppercase() }} payment recipient ${record.label}") {
            val updated = withAccessToken {
                gateway.paymentOperations.transitionRecipient(it, record, target, reason.trim())
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Recipient status updated", "${updated.label} is now ${updated.status}.")
        }
    }

    fun createPaymentCapability(request: PaymentCapabilityCreateRequest) {
        val cityId = paymentMutationScope(MANAGE_PAYMENT_CAPABILITIES, request.operatorId) ?: return
        launchMutation("Creating payment capability ${request.version}") {
            val created = withAccessToken {
                gateway.paymentOperations.createCapability(it, cityId, request)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Payment capability draft created", "${created.version} is DRAFT and not passenger-visible.")
        }
    }

    fun transitionPaymentCapability(record: PaymentCapabilityRecord, target: String, reason: String) {
        if (!paymentRecordInScope(MANAGE_PAYMENT_CAPABILITIES, record.cityId, record.operatorId)) return
        if (target !in setOf("submit", "approve", "activate") || reason.trim().length !in 3..240) {
            fail("Valid review command required", "Choose the next documented transition and enter a reason between 3 and 240 characters.")
            return
        }
        launchMutation("Moving payment capability ${record.version} through $target") {
            val updated = withAccessToken {
                gateway.paymentOperations.transitionCapability(it, record, target, reason.trim())
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Payment capability updated", "${updated.version} is now ${updated.status}.")
        }
    }

    fun verifyManualTransfer(paymentId: String, settlementReference: String) {
        if (!reconciliationRecordVisible(paymentId) || settlementReference.trim().length !in 3..120) {
            fail("Settlement evidence required", "Select a visible claim and enter its independent statement reference.")
            return
        }
        launchMutation("Verifying manual transfer") {
            withAccessToken {
                gateway.paymentOperations.verifyTransfer(
                    it, paymentId, buildPaymentIdempotencyKey("verify", paymentId), settlementReference.trim()
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Transfer reconciled", "The backend completed payment and created the driver earning atomically.")
        }
    }

    fun rejectManualTransfer(paymentId: String, reason: String) {
        if (!reconciliationRecordVisible(paymentId) || reason.trim().length !in 3..500) {
            fail("Rejection reason required", "Select a visible claim and enter a bounded correction reason.")
            return
        }
        launchMutation("Rejecting manual transfer claim") {
            withAccessToken {
                gateway.paymentOperations.rejectTransfer(
                    it, paymentId, buildPaymentIdempotencyKey("reject", paymentId), reason.trim()
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Claim rejected", "The payment returned to PENDING; no earning was created.")
        }
    }

    fun recordPaymentRefund(paymentId: String, request: PaymentRefundCreateRequest) {
        if (mutableState.value.session?.hasPermission(RECONCILE_PAYMENTS) != true || paymentId.isBlank()) {
            fail("Not authorized", "Payment reconciliation permission and a payment ID are required.")
            return
        }
        launchMutation("Recording confirmed refund") {
            val recorded = withAccessToken {
                gateway.paymentOperations.recordRefund(
                    it, paymentId, buildPaymentIdempotencyKey("refund", paymentId), request
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Refund recorded", "${recorded.amount} ${recorded.currency} was appended; the original payment remains auditable.")
        }
    }

    fun createOperatorFeePolicy(request: OperatorFeePolicyCreateRequest) {
        val cityId = pricingMutationScope(MANAGE_OPERATOR_FEE_POLICIES, request.operatorId) ?: return
        launchMutation("Creating operator-fee policy ${request.version}") {
            val created = withAccessToken {
                gateway.pricingEconomics.createOperatorFeePolicy(it, cityId, request)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Operator-fee draft created", "${created.version} is DRAFT at backend version ${created.optimisticVersion}.")
        }
    }

    fun updateOperatorFeePolicy(
        record: OperatorFeePolicyRecord,
        request: OperatorFeePolicyUpdateRequest,
    ) {
        if (!pricingRecordInScope(MANAGE_OPERATOR_FEE_POLICIES, record.cityId, record.operatorId)) return
        launchMutation("Updating operator-fee policy ${record.version}") {
            val updated = withAccessToken {
                gateway.pricingEconomics.updateOperatorFeePolicy(it, record.id, request)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Operator-fee draft saved", "The backend confirmed revision ${updated.optimisticVersion}.")
        }
    }

    fun transitionOperatorFeePolicy(record: OperatorFeePolicyRecord, target: String, reason: String) {
        if (!pricingRecordInScope(MANAGE_OPERATOR_FEE_POLICIES, record.cityId, record.operatorId)) return
        if (!validPolicyCommand(target, reason)) return
        launchMutation("Moving operator-fee policy ${record.version} to $target") {
            val updated = withAccessToken {
                gateway.pricingEconomics.transitionOperatorFeePolicy(it, record, target, reason)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Operator-fee status updated", "${updated.version} is now ${updated.status}.")
        }
    }

    fun createSchedulingPolicy(request: SchedulingPolicyCreateRequest) {
        val cityId = pricingMutationScope(MANAGE_SCHEDULING_POLICY, request.operatorId) ?: return
        launchMutation("Creating scheduling policy ${request.version}") {
            val created = withAccessToken {
                gateway.pricingEconomics.createSchedulingPolicy(it, cityId, request)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Scheduling-policy draft created", "${created.version} is DRAFT at backend version ${created.optimisticVersion}.")
        }
    }

    fun updateSchedulingPolicy(
        record: SchedulingPolicyRecord,
        request: SchedulingPolicyUpdateRequest,
    ) {
        if (!pricingRecordInScope(MANAGE_SCHEDULING_POLICY, record.cityId, record.operatorId)) return
        launchMutation("Updating scheduling policy ${record.version}") {
            val updated = withAccessToken {
                gateway.pricingEconomics.updateSchedulingPolicy(it, record.id, request)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Scheduling-policy draft saved", "The backend confirmed revision ${updated.optimisticVersion}.")
        }
    }

    fun transitionSchedulingPolicy(record: SchedulingPolicyRecord, target: String, reason: String) {
        if (!pricingRecordInScope(MANAGE_SCHEDULING_POLICY, record.cityId, record.operatorId)) return
        if (!validPolicyCommand(target, reason)) return
        launchMutation("Moving scheduling policy ${record.version} to $target") {
            val updated = withAccessToken {
                gateway.pricingEconomics.transitionSchedulingPolicy(it, record, target, reason)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Scheduling-policy status updated", "${updated.version} is now ${updated.status}.")
        }
    }

    fun createFixedRoute(request: FixedRouteCreateRequest) {
        val cityId = fixedRouteMutationScope(request.operatorId) ?: return
        launchMutation("Creating fixed route ${request.code}") {
            val created = withAccessToken {
                gateway.fixedRoutes.create(it, cityId, request)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Fixed route created", "${created.code} is ready for an immutable content version.")
        }
    }

    fun createFixedRouteVersion(route: FixedRouteRecord, request: FixedRouteVersionCreateRequest) {
        if (!fixedRouteRecordInScope(route.cityId, route.operatorId)) return
        launchMutation("Creating route version ${request.version}") {
            val created = withAccessToken {
                gateway.fixedRoutes.createVersion(it, route.id, request)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice(
                "Route draft created",
                "${created.routeCode} ${created.version} is DRAFT at backend version ${created.optimisticVersion}.",
            )
        }
    }

    fun transitionFixedRouteVersion(
        version: FixedRouteVersionRecord,
        target: String,
        reason: String,
    ) {
        if (!fixedRouteRecordInScope(version.cityId, version.operatorId)) return
        if (target !in setOf("IN_REVIEW", "PUBLISHED", "RETIRED")) {
            fail("Unsupported transition", "Refresh and choose a documented fixed-route transition.")
            return
        }
        if (reason.trim().length !in 3..240) {
            fail("Review reason required", "Enter an audited reason between 3 and 240 characters.")
            return
        }
        launchMutation("Moving route ${version.routeCode} ${version.version} to $target") {
            val updated = withAccessToken {
                gateway.fixedRoutes.transitionVersion(it, version, target, reason)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Route version updated", "${updated.routeCode} ${updated.version} is now ${updated.status}.")
        }
    }

    fun retireFixedRoute(route: FixedRouteRecord, reason: String) {
        if (!fixedRouteRecordInScope(route.cityId, route.operatorId)) return
        if (reason.trim().length !in 3..240) {
            fail("Retirement reason required", "Enter an audited reason between 3 and 240 characters.")
            return
        }
        launchMutation("Retiring fixed route ${route.code}") {
            val retired = withAccessToken {
                gateway.fixedRoutes.retireRoute(it, route.id, reason)
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice("Fixed route retired", "${retired.code} and its live versions are now retired.")
        }
    }

    fun selectDriverApplication(applicationId: String) {
        val current = mutableState.value
        if (current.session?.hasPermission(REVIEW_DRIVER_APPLICATIONS) != true || current.interactionLocked) return
        scope.launch {
            mutate { it.copy(mutationLabel = "Loading driver application", error = null, notice = null) }
            try {
                val detail = withAccessToken { gateway.driverApplication(it, applicationId) }
                mutate { it.copy(selectedDriverApplication = detail, mutationLabel = null) }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleMutationFailure(error)
            }
        }
    }

    fun downloadDriverApplicationDocument(applicationId: String, documentId: String) {
        val current = mutableState.value
        val selected = current.selectedDriverApplication?.application
        if (
            current.session?.hasPermission(REVIEW_DRIVER_APPLICATIONS) != true ||
            selected?.id != applicationId
        ) {
            fail("Application review required", "Select the application inside your granted city scope before reading a document.")
            return
        }
        if (!browserProtectedDocumentDownloadAvailable) {
            fail("Browser download unavailable", "Use a supported browser build for protected document retrieval.")
            return
        }
        launchMutation("Retrieving protected document") {
            val download = withAccessToken {
                gateway.downloadDriverApplicationDocument(it, applicationId, documentId)
            }
            saveProtectedDocumentDownload(download)
            mutate {
                it.copy(
                    notice = OperationsMessage(
                        "Protected document downloaded",
                        "The copy is for this review task only. Do not upload it to notes, analytics, or shared storage.",
                    ),
                )
            }
        }
    }

    fun decideDriverApplication(request: DriverApplicationDecisionRequest) {
        val current = mutableState.value
        val selected = current.selectedDriverApplication?.application
        if (current.session?.hasPermission(REVIEW_DRIVER_APPLICATIONS) != true || selected == null) {
            fail("Application review required", "Select an application inside your granted city scope.")
            return
        }
        if (request.expectedVersion != selected.optimisticVersion) {
            fail("Application version changed", "Refresh the application before recording a decision.")
            return
        }
        if (request.reasonCode.length !in 3..64 || request.applicantSafeMessage.trim().length !in 3..500) {
            fail("Decision details required", "Choose a reason and enter an applicant-safe message of 3 to 500 characters.")
            return
        }
        val idempotencyKey = buildReviewIdempotencyKey(selected.id)
        launchMutation("Recording ${request.decision.lowercase().replace('_', ' ')}") {
            val detail = withAccessToken {
                gateway.decideDriverApplication(it, selected.id, idempotencyKey, request)
            }
            reloadNow(mutableState.value.scope, initial = false)
            mutate {
                it.copy(
                    selectedDriverApplication = detail,
                    notice = OperationsMessage(
                        "Driver application updated",
                        "${detail.applicantDisplayName} is now ${detail.application.status} at backend version ${detail.application.optimisticVersion}.",
                    ),
                )
            }
        }
    }

    fun decideCityAuthorization(
        authorizationId: String,
        expectedVersion: Int,
        action: CityAuthorizationAction,
        reasonCode: String,
        confirmation: String,
    ) {
        val current = mutableState.value
        val application = current.selectedDriverApplication?.application
        val authorization = application?.authorization
        if (current.session?.hasPermission(REVIEW_DRIVER_APPLICATIONS) != true ||
            application == null || authorization == null || authorization.id != authorizationId ||
            application.optimisticVersion != expectedVersion ||
            action !in cityAuthorizationActions(authorization.status) || reasonCode !in action.reasons ||
            confirmation.trim() != authorization.id
        ) {
            fail("Review the city authorization", "Refresh the application, choose a valid reason, and confirm the exact authorization ID.")
            return
        }
        val key = buildReviewIdempotencyKey(application.id)
        launchMutation("Recording city authorization decision") {
            val detail = withAccessToken {
                gateway.decideCityAuthorization(it, application.id, key,
                    CityAuthorizationDecisionRequest(expectedVersion, action.name, reasonCode))
            }
            reloadNow(mutableState.value.scope, initial = false)
            mutate { it.copy(
                selectedDriverApplication = detail,
                notice = OperationsMessage("City authorization updated",
                    "${detail.application.cityCode}: ${detail.application.authorization?.status}. Existing ride history is preserved."),
            ) }
        }
    }

    fun applyAccountSecurityAction(
        targetUserId: String,
        action: AccountSecurityAction,
        reasonCode: String,
        caseReference: String,
        confirmation: String,
    ) {
        val current = mutableState.value
        if (current.session?.hasPermission(MANAGE_ACCOUNT_SECURITY) != true) {
            fail("Not authorized", "The dedicated account-security permission is required.")
            return
        }
        val inputError = accountSecurityInputError(
            marketId = current.scope.marketId,
            targetUserId = targetUserId,
            action = action,
            reasonCode = reasonCode,
            caseReference = caseReference,
            confirmation = confirmation,
        )
        if (inputError != null) {
            fail("Review the containment command", inputError)
            return
        }
        val marketId = current.scope.marketId ?: return
        val userId = targetUserId.trim().lowercase()
        launchMutation("Applying ${action.label.lowercase()}") {
            val result = withAccessToken {
                gateway.accountSecurity.apply(
                    accessToken = it,
                    marketId = marketId,
                    targetUserId = userId,
                    action = action,
                    idempotencyKey = buildAccountSecurityIdempotencyKey(action, userId),
                    request = AccountSecurityActionRequest(
                        reasonCode = reasonCode,
                        caseReference = caseReference.trim().uppercase(),
                    ),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            notice(
                "Account command recorded",
                "${result.status}: ${result.sessionsRevoked} sessions and ${result.deviceRegistrationsRevoked} push registrations revoked.",
            )
        }
    }

    fun selectSecurityIncident(incidentId: String) {
        val current = mutableState.value
        val visible = current.snapshot?.securityIncidents?.incidents?.items
            ?.any { it.id == incidentId } == true
        if (current.session?.hasPermission(MANAGE_SECURITY_INCIDENTS) != true || !visible) {
            fail("Incident not available", "Refresh the authorized incident queue and select a visible record.")
            return
        }
        launchMutation("Loading security incident") {
            loadSecurityIncidentNow(incidentId)
        }
    }

    fun createSecurityIncident(
        severity: SecurityIncidentSeverity,
        category: SecurityIncidentCategory,
        summary: String,
        detectedAt: String,
        containmentDueAt: String,
        cityScoped: Boolean,
        confirmation: String,
    ) {
        val current = mutableState.value
        if (current.session?.hasPermission(MANAGE_SECURITY_INCIDENTS) != true) {
            fail("Not authorized", "The dedicated security-incident permission is required.")
            return
        }
        val inputError = securityIncidentCreateInputError(
            current.scope.marketId,
            summary,
            detectedAt,
            containmentDueAt,
        )
        if (inputError != null || confirmation.trim().uppercase() != "OPEN INCIDENT") {
            fail(
                "Review the incident",
                inputError ?: "Type OPEN INCIDENT to create the restricted incident record.",
            )
            return
        }
        val marketId = current.scope.marketId ?: return
        launchMutation("Opening security incident") {
            val created = withAccessToken {
                gateway.securityIncidents.create(
                    accessToken = it,
                    idempotencyKey = buildSecurityIncidentIdempotencyKey("create", marketId),
                    request = SecurityIncidentCreateRequest(
                        marketId = marketId,
                        cityId = current.scope.cityId.takeIf { cityScoped },
                        severity = severity.name,
                        category = category.name,
                        summary = summary.trim(),
                        detectedAt = detectedAt.trim(),
                        containmentDueAt = containmentDueAt.trim(),
                    ),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            loadSecurityIncidentNow(created.id)
            notice("Security incident opened", "${created.reference} is assigned to the reporting lead.")
        }
    }

    fun appendSecurityIncidentTimeline(
        kind: SecurityIncidentTimelineKind,
        summary: String,
        occurredAt: String,
        auditLogId: String,
        externalReference: String,
        confirmation: String,
    ) {
        val current = mutableState.value
        val incident = current.selectedSecurityIncident
        if (current.session?.hasPermission(MANAGE_SECURITY_INCIDENTS) != true) {
            fail("Not authorized", "The dedicated security-incident permission is required.")
            return
        }
        val inputError = securityIncidentTimelineInputError(
            incident,
            summary,
            occurredAt,
            auditLogId,
            externalReference,
            confirmation,
        )
        if (inputError != null) {
            fail("Review the timeline fact", inputError)
            return
        }
        incident ?: return
        launchMutation("Appending immutable incident fact") {
            withAccessToken {
                gateway.securityIncidents.appendTimeline(
                    accessToken = it,
                    incidentId = incident.id,
                    idempotencyKey = buildSecurityIncidentIdempotencyKey("timeline", incident.id),
                    request = SecurityIncidentTimelineCreateRequest(
                        kind = kind.name,
                        summary = summary.trim(),
                        occurredAt = occurredAt.trim(),
                        auditLogId = auditLogId.trim().ifBlank { null },
                        externalReference = externalReference.trim().ifBlank { null },
                    ),
                )
            }
            loadSecurityIncidentNow(incident.id)
            notice("Timeline updated", "A new immutable ${kind.label.lowercase()} fact was recorded.")
        }
    }

    fun transitionSecurityIncident(
        transition: SecurityIncidentTransition,
        summary: String,
        occurredAt: String,
        postmortemDueAt: String,
        confirmation: String,
    ) {
        val current = mutableState.value
        val incident = current.selectedSecurityIncident
        if (current.session?.hasPermission(MANAGE_SECURITY_INCIDENTS) != true) {
            fail("Not authorized", "The dedicated security-incident permission is required.")
            return
        }
        val inputError = securityIncidentTransitionInputError(
            incident,
            transition,
            summary,
            occurredAt,
            postmortemDueAt,
            confirmation,
        )
        if (inputError != null) {
            fail("Review the lifecycle action", inputError)
            return
        }
        incident ?: return
        launchMutation("Applying ${transition.label.lowercase()}") {
            withAccessToken {
                gateway.securityIncidents.transition(
                    accessToken = it,
                    incidentId = incident.id,
                    idempotencyKey = buildSecurityIncidentIdempotencyKey("transition", incident.id),
                    request = SecurityIncidentTransitionRequest(
                        transition = transition.name,
                        expectedVersion = incident.optimisticVersion,
                        summary = summary.trim(),
                        occurredAt = occurredAt.trim(),
                        postmortemDueAt = postmortemDueAt.trim().ifBlank { null },
                    ),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            loadSecurityIncidentNow(incident.id)
            notice("Incident state updated", "The backend accepted ${transition.targetStatus}.")
        }
    }

    fun completeSecurityIncidentPostmortem(
        outcome: SecurityIncidentPostmortemOutcome,
        summary: String,
        occurredAt: String,
        auditLogId: String,
        externalReference: String,
        confirmation: String,
    ) {
        val current = mutableState.value
        val incident = current.selectedSecurityIncident
        if (current.session?.hasPermission(MANAGE_SECURITY_INCIDENTS) != true) {
            fail("Not authorized", "The dedicated security-incident permission is required.")
            return
        }
        val inputError = securityIncidentPostmortemInputError(
            incident,
            outcome,
            summary,
            occurredAt,
            auditLogId,
            externalReference,
            confirmation,
        )
        if (inputError != null) {
            fail("Review the postmortem completion", inputError)
            return
        }
        incident ?: return
        launchMutation("Completing incident postmortem") {
            withAccessToken {
                gateway.securityIncidents.completePostmortem(
                    accessToken = it,
                    incidentId = incident.id,
                    idempotencyKey = buildSecurityIncidentIdempotencyKey(
                        "postmortem",
                        incident.id,
                    ),
                    request = SecurityIncidentPostmortemCompleteRequest(
                        expectedVersion = incident.optimisticVersion,
                        outcome = outcome.name,
                        summary = summary.trim(),
                        occurredAt = occurredAt.trim(),
                        auditLogId = auditLogId.trim().ifBlank { null },
                        externalReference = externalReference.trim().ifBlank { null },
                    ),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            loadSecurityIncidentNow(incident.id)
            notice(
                "Postmortem completed",
                "The backend recorded ${outcome.label.lowercase()} with immutable evidence.",
            )
        }
    }

    fun assignSecurityIncidentResponsibility(
        responsibility: SecurityIncidentResponsibility,
        assignedUserId: String,
        occurredAt: String,
        externalReference: String,
        confirmation: String,
    ) {
        val current = mutableState.value
        val incident = current.selectedSecurityIncident
        if (current.session?.hasPermission(MANAGE_SECURITY_INCIDENTS) != true) {
            fail("Not authorized", "The dedicated security-incident permission is required.")
            return
        }
        val inputError = securityIncidentResponsibilityInputError(
            incident,
            assignedUserId,
            occurredAt,
            externalReference,
            confirmation,
        )
        if (inputError != null) {
            fail("Review the responsibility assignment", inputError)
            return
        }
        incident ?: return
        launchMutation("Assigning incident responsibility") {
            withAccessToken {
                gateway.securityIncidents.assignResponsibility(
                    accessToken = it,
                    incidentId = incident.id,
                    responsibility = responsibility.name,
                    idempotencyKey = buildSecurityIncidentIdempotencyKey(
                        "responsibility-${responsibility.name.lowercase()}",
                        incident.id,
                    ),
                    request = SecurityIncidentResponsibilityAssignRequest(
                        expectedVersion = incident.optimisticVersion,
                        assignedUserId = assignedUserId.trim(),
                        occurredAt = occurredAt.trim(),
                        externalReference = externalReference.trim(),
                    ),
                )
            }
            reloadNow(mutableState.value.scope, initial = false)
            loadSecurityIncidentNow(incident.id)
            notice(
                "Responsibility assigned",
                "${responsibility.label} now has an authoritative active assignee.",
            )
        }
    }

    private suspend fun loadSecurityIncidentNow(incidentId: String) {
        val detail = withAccessToken { gateway.securityIncidents.get(it, incidentId) }
        val timeline = withAccessToken { gateway.securityIncidents.timeline(it, incidentId) }
        val responsibilities = withAccessToken {
            gateway.securityIncidents.responsibilities(it, incidentId)
        }
        mutate {
            it.copy(
                selectedSecurityIncident = detail,
                securityIncidentTimeline = timeline,
                securityIncidentResponsibilities = responsibilities,
            )
        }
    }

    fun logout() {
        val accessToken = tokens?.accessToken
        reloadJob?.cancel()
        reloadJob = scope.launch {
            var logoutError: OperationsMessage? = null
            if (accessToken != null) {
                try {
                    gateway.logout(accessToken)
                } catch (cancelled: CancellationException) {
                    throw cancelled
                } catch (_: Throwable) {
                    logoutError = OperationsMessage(
                        "Local session cleared",
                        "The server-side logout could not be confirmed. Do not reuse this browser session; the short operations access token will expire.",
                    )
                }
            }
            tokens = null
            mutate {
                OperationsUiState(
                    apiBaseUrl = it.apiBaseUrl,
                    isLocalDevelopment = it.isLocalDevelopment,
                    error = logoutError,
                )
            }
        }
    }

    fun dismissError() = mutate { it.copy(error = null) }
    fun dismissNotice() = mutate { it.copy(notice = null) }

    private fun launchMutation(label: String, command: suspend () -> Unit) {
        if (mutableState.value.interactionLocked) return
        scope.launch {
            mutate { it.copy(mutationLabel = label, error = null, notice = null) }
            try {
                command()
                mutate { it.copy(mutationLabel = null) }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleMutationFailure(error)
            }
        }
    }

    private suspend fun handleMutationFailure(error: Throwable) {
        diagnoseLocalFailure("mutation", error)
        if (error is OperationsApiException && error.statusCode == 401) {
            expireSession()
            return
        }
        if (error is OperationsApiException && error.statusCode == 409) {
            runCatching { reloadNow(mutableState.value.scope, initial = false) }
        }
        if (
            error is OperationsApiException &&
            error.statusCode == 403 &&
            error.message.contains("Recent operations MFA", ignoreCase = true)
        ) {
            mutate {
                it.copy(
                    mutationLabel = null,
                    isRefreshing = false,
                    showMfaStepUp = true,
                    error = OperationsMessage(
                        "Reverify before continuing",
                        "Enter a current authenticator or recovery code. The original command was not executed; confirm it again after verification.",
                    ),
                )
            }
            return
        }
        mutate {
            it.copy(
                mutationLabel = null,
                isRefreshing = false,
                error = error.toMessage(),
            )
        }
    }

    private fun fail(title: String, detail: String) = mutate {
        it.copy(mutationLabel = null, error = OperationsMessage(title, detail), notice = null)
    }

    private fun pricingMutationScope(permission: String, operatorId: String): String? {
        val current = mutableState.value
        val cityId = current.scope.cityId
        if (
            current.session?.hasPermission(permission) != true || cityId == null ||
            current.scope.operatorId == null || current.scope.operatorId != operatorId
        ) {
            fail(
                "Pricing scope required",
                "Select one authorized city and operator with the required pricing permission.",
            )
            return null
        }
        return cityId
    }

    private fun paymentMutationScope(permission: String, operatorId: String): String? {
        val current = mutableState.value
        val cityId = current.scope.cityId
        if (
            current.session?.hasPermission(permission) != true || cityId == null ||
            current.scope.operatorId == null || current.scope.operatorId != operatorId
        ) {
            fail("Payment scope required", "Select one authorized city and operator with the required payment permission.")
            return null
        }
        return cityId
    }

    private fun paymentRecordInScope(permission: String, cityId: String, operatorId: String): Boolean {
        val selectedCity = paymentMutationScope(permission, operatorId) ?: return false
        if (cityId != selectedCity) {
            fail("Outside active scope", "Refresh and select the city that owns this payment record.")
            return false
        }
        return true
    }

    private fun reconciliationRecordVisible(paymentId: String): Boolean {
        val current = mutableState.value
        return current.session?.hasPermission(RECONCILE_PAYMENTS) == true &&
            current.snapshot?.paymentOperations?.manualTransfers?.items?.any { it.paymentId == paymentId } == true
    }

    private fun pricingRecordInScope(permission: String, cityId: String, operatorId: String): Boolean {
        val selectedCityId = pricingMutationScope(permission, operatorId) ?: return false
        if (cityId != selectedCityId) {
            fail("Outside active scope", "Refresh and select the city that owns this policy version.")
            return false
        }
        return true
    }

    private fun fixedRouteMutationScope(operatorId: String): String? {
        val current = mutableState.value
        val cityId = current.scope.cityId
        if (
            current.session?.hasPermission(MANAGE_FIXED_ROUTES) != true || cityId == null ||
            current.scope.operatorId == null || current.scope.operatorId != operatorId
        ) {
            fail(
                "Fixed-route scope required",
                "Select one authorized city and operator with fixed-route permission.",
            )
            return null
        }
        return cityId
    }

    private fun fixedRouteRecordInScope(cityId: String, operatorId: String): Boolean {
        val selectedCityId = fixedRouteMutationScope(operatorId) ?: return false
        if (cityId != selectedCityId) {
            fail("Outside active scope", "Refresh and select the city that owns this fixed route.")
            return false
        }
        return true
    }

    private fun grantBelongsToSelectedMarket(
        grant: AdministrativeGrantRecord,
        current: OperationsUiState,
    ): Boolean {
        val marketId = current.scope.marketId ?: return false
        return when {
            grant.marketId != null -> grant.marketId == marketId
            grant.operatorId != null -> current.snapshot?.operators?.items?.any {
                it.id == grant.operatorId && it.marketId == marketId
            } == true
            grant.cityId != null -> current.snapshot?.cities?.items?.any {
                it.id == grant.cityId && it.marketId == marketId
            } == true
            else -> false
        }
    }

    private fun validPolicyCommand(target: String, reason: String): Boolean {
        if (target !in setOf("IN_REVIEW", "ACTIVE")) {
            fail("Unsupported transition", "Refresh and choose the documented policy transition.")
            return false
        }
        if (reason.trim().length !in 3..240) {
            fail("Review reason required", "Enter an audited reason between 3 and 240 characters.")
            return false
        }
        return true
    }

    private fun notice(title: String, detail: String) = mutate {
        it.copy(mutationLabel = null, notice = OperationsMessage(title, detail), error = null)
    }

    private fun reload(requestedScope: OperationsScope) {
        reloadJob?.cancel()
        reloadJob = scope.launch {
            try {
                reloadNow(requestedScope, initial = mutableState.value.snapshot == null)
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                diagnoseLocalFailure("scope reload", error)
                if (error is OperationsApiException && error.statusCode == 401) {
                    expireSession()
                } else {
                    mutate {
                        it.copy(
                            isInitialLoading = false,
                            isRefreshing = false,
                            error = error.toMessage(),
                        )
                    }
                }
            }
        }
    }

    private suspend fun reloadNow(requestedScope: OperationsScope, initial: Boolean) {
        val session = mutableState.value.session
            ?: throw OperationsApiException(401, "The operations session is no longer available.")
        mutate {
            it.copy(
                isInitialLoading = initial,
                isRefreshing = !initial,
                error = null,
            )
        }
        val snapshot = withAccessToken {
            gateway.loadSnapshot(it, session, requestedScope)
        }
        val normalizedScope = snapshot.normalizedScope(requestedScope)
        val destinations = availableDestinations(session.permissions)
        mutate {
            it.copy(
                scope = normalizedScope,
                snapshot = snapshot,
                selectedDriverApplication = null,
                selectedSupportCase = null,
                selectedSafetyCase = null,
                selectedSecurityIncident = null,
                securityIncidentTimeline = null,
                securityIncidentResponsibilities = null,
                destination = it.destination.takeIf { destination -> destination in destinations }
                    ?: destinations.firstOrNull()
                    ?: OperationsDestination.ROLLOUT,
                isInitialLoading = false,
                isRefreshing = false,
            )
        }
    }

    private suspend fun <T> withAccessToken(block: suspend (String) -> T): T {
        val active = tokens
            ?: throw OperationsApiException(401, "The operations session is no longer available.")
        return try {
            block(active.accessToken)
        } catch (error: OperationsApiException) {
            if (error.statusCode != 401) throw error
            val refreshed = gateway.refresh(active.refreshToken, active.csrfToken)
            tokens = refreshed
            mutate { it.copy(authenticationStrength = refreshed.authenticationStrength) }
            block(refreshed.accessToken)
        }
    }

    private fun expireSession() {
        tokens = null
        mutate {
            OperationsUiState(
                apiBaseUrl = it.apiBaseUrl,
                isLocalDevelopment = it.isLocalDevelopment,
                error = OperationsMessage(
                    "Session expired",
                    "Sign in again. No failed administrative command was replayed.",
                ),
            )
        }
    }

    private fun mutate(transform: (OperationsUiState) -> OperationsUiState) {
        mutableState.value = transform(mutableState.value)
    }

    private fun diagnoseLocalFailure(operation: String, error: Throwable) {
        if (mutableState.value.isLocalDevelopment) {
            // Never include request bodies, credentials, or token values. This
            // bounded local-only diagnostic makes browser transport/decoding
            // failures actionable while hosted environments remain quiet.
            println(
                "TaxiMobile operations $operation failed: " +
                    "${error::class.simpleName ?: "Error"}: ${error.message ?: "no detail"}"
            )
        }
    }
}

private fun buildReviewIdempotencyKey(applicationId: String): String =
    "driver-review-${applicationId.take(12)}-${Clock.System.now().toEpochMilliseconds()}-${Random.nextInt(100000, 999999)}"

private fun buildCaseIdempotencyKey(operation: String, caseId: String): String =
    "$operation-${caseId.take(12)}-${Clock.System.now().toEpochMilliseconds()}-${Random.nextInt(100000, 999999)}"

private fun buildPaymentIdempotencyKey(operation: String, paymentId: String): String =
    "payment-$operation-${paymentId.take(12)}-${Clock.System.now().toEpochMilliseconds()}-${Random.nextInt(100000, 999999)}"

private fun buildAccountSecurityIdempotencyKey(action: AccountSecurityAction, userId: String): String =
    "account-${action.name.lowercase()}-${userId.take(12)}-${Clock.System.now().toEpochMilliseconds()}-${Random.nextInt(100000, 999999)}"

private fun buildSecurityIncidentIdempotencyKey(operation: String, resourceId: String): String =
    "incident-$operation-${resourceId.take(12)}-${Clock.System.now().toEpochMilliseconds()}-${Random.nextInt(100000, 999999)}"

private fun buildGrantIdempotencyKey(operation: String, resourceId: String): String =
    "grant-$operation-${resourceId.take(12)}-${Clock.System.now().toEpochMilliseconds()}-${Random.nextInt(100000, 999999)}"

private fun Throwable.toMessage(signIn: Boolean = false): OperationsMessage = when (this) {
    is OperationsApiException -> when (statusCode) {
        401 -> OperationsMessage(
            if (signIn) "Sign-in failed" else "Session rejected",
            message,
        )
        403 -> OperationsMessage("Outside granted scope", message)
        404 -> OperationsMessage("Resource not available", message)
        409 -> OperationsMessage(
            "State changed",
            "$message The current backend state has been reloaded; review it before trying a new command.",
        )
        429 -> OperationsMessage("Too many attempts", message)
        503 -> OperationsMessage("Operations access unavailable", message)
        else -> OperationsMessage("Operations request failed", message)
    }
    else -> OperationsMessage(
        "Cannot reach the operations API",
        "Check that the backend is running at the displayed API URL and that its exact CORS origin allows this web app.",
    )
}
