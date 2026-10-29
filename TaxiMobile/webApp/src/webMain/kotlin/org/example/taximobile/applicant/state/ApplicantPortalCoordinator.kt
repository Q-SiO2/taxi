package org.example.taximobile.applicant.state

import org.example.taximobile.feature.ui.text.UiMessage
import taximobile.shared.generated.resources.*
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.auth.SecureTokenStore
import org.example.taximobile.data.auth.StoredTokens
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.drivers.DriverApplicationAnswerDraft
import org.example.taximobile.domain.drivers.DriverApplicationEvidenceDraft
import org.example.taximobile.domain.drivers.DriverCityApplication
import org.example.taximobile.domain.drivers.DriverCityApplicationSummary
import org.example.taximobile.domain.drivers.DriverCredential
import org.example.taximobile.domain.drivers.DriverGateway
import org.example.taximobile.domain.drivers.DriverRecruitmentGateway
import org.example.taximobile.domain.drivers.DriverVehicle
import org.example.taximobile.domain.drivers.RecruitingCity
import org.example.taximobile.domain.drivers.VehicleRegistration
import org.example.taximobile.feature.auth.AuthenticationSessionCoordinator
import org.example.taximobile.feature.auth.AuthenticationState

enum class ApplicantSessionPhase { SIGNED_OUT, SIGNING_IN, SIGNED_IN }

enum class ApplicantAuthMode { SIGN_IN, CREATE_ACCOUNT }

data class ApplicantPortalMessage(
    val title: String,
    val detail: String,
    val localizedTitle: UiMessage? = null,
    val localizedDetail: UiMessage? = null,
) {
    constructor(title: UiMessage, detail: UiMessage) : this("", "", title, detail)
}

data class ApplicantPortalState(
    val apiBaseUrl: String,
    val sessionPhase: ApplicantSessionPhase = ApplicantSessionPhase.SIGNED_OUT,
    val authMode: ApplicantAuthMode = ApplicantAuthMode.SIGN_IN,
    val account: CurrentAccount? = null,
    val recruitingCities: List<RecruitingCity> = emptyList(),
    val catalogUnavailable: Boolean = false,
    val applications: List<DriverCityApplicationSummary> = emptyList(),
    val selectedApplication: DriverCityApplication? = null,
    val vehicles: List<DriverVehicle> = emptyList(),
    val credentials: List<DriverCredential> = emptyList(),
    val busyLabel: UiMessage? = null,
    val error: ApplicantPortalMessage? = null,
    val notice: ApplicantPortalMessage? = null,
) {
    val interactionLocked: Boolean get() = busyLabel != null || sessionPhase == ApplicantSessionPhase.SIGNING_IN
}

/**
 * Browser-only token storage. A refresh intentionally signs the applicant out;
 * bearer and refresh tokens are never copied into URL or persistent Web APIs.
 */
class InMemoryApplicantTokenStore : SecureTokenStore {
    private var value: StoredTokens? = null

    override suspend fun tokens(): StoredTokens? = value

    override suspend fun save(accessToken: String, refreshToken: String) {
        value = StoredTokens(accessToken, refreshToken)
    }

    override suspend fun clear() {
        value = null
    }

    suspend fun accessToken(): String = value?.accessToken ?: throw AuthenticationRejectedException()
}

/** Coordinates the public catalog and the signed-in applicant's own records only. */
class ApplicantPortalCoordinator(
    private val authentication: AuthenticationSessionCoordinator,
    private val recruitment: DriverRecruitmentGateway,
    private val driver: DriverGateway,
    private val scope: CoroutineScope,
    apiBaseUrl: String,
) {
    private val mutableState = MutableStateFlow(ApplicantPortalState(apiBaseUrl = apiBaseUrl))
    val state: StateFlow<ApplicantPortalState> = mutableState.asStateFlow()

    init {
        refreshCatalog()
    }

    fun setAuthMode(mode: ApplicantAuthMode) = mutate {
        if (it.interactionLocked) it else it.copy(authMode = mode, error = null, notice = null)
    }

    fun login(identifier: String, password: String) {
        val validation = validateApplicantLogin(identifier, password)
        if (validation != null) {
            fail(UiMessage(Res.string.web_check_details), validation)
            return
        }
        if (mutableState.value.interactionLocked) return
        scope.launch {
            mutate {
                it.copy(
                    sessionPhase = ApplicantSessionPhase.SIGNING_IN,
                    busyLabel = UiMessage(Res.string.web_app_busy_sign_in),
                    error = null,
                    notice = null,
                )
            }
            try {
                when (val result = authentication.login(identifier.trim(), password, "Applicant web portal")) {
                    is AuthenticationState.Authenticated -> loadSignedIn(result.account)
                    is AuthenticationState.Failure -> signOutWithError(
                        UiMessage(Res.string.web_auth_rejected_title), result.message,
                    )
                    else -> signOutWithError(UiMessage(Res.string.web_auth_rejected_title), UiMessage(Res.string.web_request_unconfirmed))
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleFailure(error)
            }
        }
    }

    fun register(
        displayName: String,
        email: String,
        phoneNumber: String,
        password: String,
    ) {
        val validation = validateApplicantRegistration(displayName, email, phoneNumber, password)
        if (validation != null) {
            fail(UiMessage(Res.string.web_check_details), validation)
            return
        }
        if (mutableState.value.interactionLocked) return
        scope.launch {
            mutate { it.copy(busyLabel = UiMessage(Res.string.web_app_busy_create), error = null, notice = null) }
            try {
                when (val result =
                    authentication.register(
                        displayName = displayName.trim(),
                        email = email.trim().ifBlank { null },
                        phoneNumber = phoneNumber.trim().ifBlank { null },
                        password = password,
                    )
                ) {
                    AuthenticationState.Unauthenticated -> mutate {
                        it.copy(
                            authMode = ApplicantAuthMode.SIGN_IN,
                            busyLabel = null,
                            notice = ApplicantPortalMessage(
                                UiMessage(Res.string.web_account_created_title),
                                UiMessage(Res.string.web_account_created_detail),
                            ),
                        )
                    }
                    is AuthenticationState.Failure -> fail(UiMessage(Res.string.web_error_title), result.message)
                    else -> fail(UiMessage(Res.string.web_error_title), UiMessage(Res.string.web_request_unconfirmed))
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleFailure(error)
            }
        }
    }

    fun refresh() {
        val account = mutableState.value.account
        if (account == null) refreshCatalog() else launchBusy(UiMessage(Res.string.web_app_busy_refresh)) { loadSignedIn(account) }
    }

    fun selectApplication(applicationId: String) = launchBusy(UiMessage(Res.string.web_app_busy_load)) {
        val application = recruitment.application(applicationId)
        reloadOwnedData(selected = application)
    }

    fun createApplication(cityId: String) = launchBusy(UiMessage(Res.string.web_app_busy_start)) {
        val account = requireNotNull(mutableState.value.account)
        val application = recruitment.createApplication(cityId, account.displayName)
        reloadOwnedData(selected = application)
    }

    fun saveApplication(
        applicationId: String,
        expectedVersion: Int,
        answers: List<DriverApplicationAnswerDraft>,
        evidence: List<DriverApplicationEvidenceDraft>,
        removeAnswerItemIds: List<String>,
        removeEvidenceItemIds: List<String>,
    ) = launchBusy(UiMessage(Res.string.web_app_busy_save)) {
        val application = recruitment.updateApplication(
            applicationId = applicationId,
            expectedVersion = expectedVersion,
            answers = answers,
            evidence = evidence,
            removeAnswerItemIds = removeAnswerItemIds,
            removeEvidenceItemIds = removeEvidenceItemIds,
        )
        reloadOwnedData(
            selected = application,
            notice = ApplicantPortalMessage(
                UiMessage(Res.string.web_app_saved_title),
                UiMessage(Res.string.web_app_version_confirmed, listOf(application.optimisticVersion)),
            ),
        )
    }

    fun submitApplication(applicationId: String) = launchBusy(UiMessage(Res.string.web_app_busy_submit)) {
        val application = recruitment.submitApplication(applicationId)
        reloadOwnedData(
            selected = application,
            notice = ApplicantPortalMessage(
                UiMessage(Res.string.web_app_submitted_title),
                UiMessage(Res.string.web_app_submitted_detail),
            ),
        )
    }

    fun withdrawApplication(applicationId: String) = launchBusy(UiMessage(Res.string.web_app_busy_withdraw)) {
        val application = recruitment.withdrawApplication(applicationId)
        reloadOwnedData(
            selected = application,
            notice = ApplicantPortalMessage(
                UiMessage(Res.string.web_app_withdrawn_title),
                UiMessage(Res.string.web_app_withdrawn_detail),
            ),
        )
    }

    fun uploadDocument(
        applicationId: String,
        requirementItemId: String,
        expectedVersion: Int,
    ) = launchBusy(UiMessage(Res.string.web_app_busy_choose)) {
        val selected = pickBrowserDriverDocument() ?: return@launchBusy
        mutate { it.copy(busyLabel = UiMessage(Res.string.web_app_busy_scan)) }
        val application = recruitment.uploadDocument(
            applicationId,
            requirementItemId,
            expectedVersion,
            selected,
        )
        reloadOwnedData(
            selected = application,
            notice = ApplicantPortalMessage(
                UiMessage(Res.string.web_app_document_saved),
                UiMessage(Res.string.web_app_version_confirmed, listOf(application.optimisticVersion)),
            ),
        )
    }

    fun deleteDocument(
        applicationId: String,
        documentId: String,
        expectedVersion: Int,
    ) = launchBusy(UiMessage(Res.string.web_app_busy_delete)) {
        val application = recruitment.deleteDocument(
            applicationId,
            documentId,
            expectedVersion,
        )
        reloadOwnedData(
            selected = application,
            notice = ApplicantPortalMessage(
                UiMessage(Res.string.web_app_document_deleted),
                UiMessage(Res.string.web_app_document_deleted_detail),
            ),
        )
    }

    fun registerVehicle(vehicle: VehicleRegistration) = launchBusy(UiMessage(Res.string.web_app_busy_vehicle)) {
        driver.registerVehicle(vehicle)
        reloadOwnedData(selected = mutableState.value.selectedApplication)
    }

    fun logout() {
        if (mutableState.value.interactionLocked) return
        scope.launch {
            authentication.logout()
            val cities = runCatching { recruitment.recruitingCities() }.getOrDefault(emptyList())
            mutate {
                ApplicantPortalState(
                    apiBaseUrl = it.apiBaseUrl,
                    recruitingCities = cities,
                    notice = ApplicantPortalMessage(UiMessage(Res.string.web_app_signed_out), UiMessage(Res.string.web_app_signed_out_detail)),
                )
            }
        }
    }

    fun dismissError() = mutate { it.copy(error = null) }
    fun dismissNotice() = mutate { it.copy(notice = null) }

    private fun refreshCatalog() {
        if (mutableState.value.interactionLocked) return
        scope.launch {
            try {
                val cities = recruitment.recruitingCities()
                mutate { it.copy(recruitingCities = cities, catalogUnavailable = false, error = null) }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleFailure(error, publicCatalog = true)
            }
        }
    }

    private suspend fun loadSignedIn(account: CurrentAccount) {
        mutate {
            it.copy(
                sessionPhase = ApplicantSessionPhase.SIGNED_IN,
                account = account,
                busyLabel = UiMessage(Res.string.web_app_busy_applications),
                error = null,
            )
        }
        reloadOwnedData(selected = mutableState.value.selectedApplication)
    }

    private suspend fun reloadOwnedData(
        selected: DriverCityApplication?,
        notice: ApplicantPortalMessage? = null,
    ) {
        val cities = recruitment.recruitingCities()
        val applications = recruitment.applications()
        val selectedId = selected?.id ?: mutableState.value.selectedApplication?.id
            ?: applications.firstOrNull()?.id
        // Keep the selection, not its cached authority. A reviewer or vehicle
        // change may have advanced this record since the last rendered detail
        // (or even since an applicant command returned). Refresh the detail too.
        val resolvedSelection = selectedId?.let { recruitment.application(it) }
        val vehicles = if (applications.isEmpty()) emptyList() else driver.vehicles()
        val credentials = if (applications.isEmpty()) emptyList() else driver.credentials()
        mutate {
            it.copy(
                sessionPhase = ApplicantSessionPhase.SIGNED_IN,
                recruitingCities = cities,
                catalogUnavailable = false,
                applications = applications,
                selectedApplication = resolvedSelection,
                vehicles = vehicles,
                credentials = credentials,
                busyLabel = null,
                error = null,
                notice = notice,
            )
        }
    }

    private fun launchBusy(label: UiMessage, command: suspend () -> Unit) {
        val current = mutableState.value
        if (current.sessionPhase != ApplicantSessionPhase.SIGNED_IN || current.interactionLocked) return
        scope.launch {
            mutate { it.copy(busyLabel = label, error = null, notice = null) }
            try {
                command()
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleFailure(error)
            }
        }
    }

    private suspend fun handleFailure(error: Throwable, publicCatalog: Boolean = false) {
        // A generic 503 does not establish whether protected storage failed or
        // whether an upload was accepted. Preserve that uncertainty explicitly.
        if (error is AuthenticationRejectedException) {
            authentication.logout()
            signOutWithError(UiMessage(Res.string.web_session_title), UiMessage(Res.string.web_session_detail))
        } else {
            val message = applicantFailureMessage(error, publicCatalog = publicCatalog)
            mutate {
                it.copy(busyLabel = null,
                    catalogUnavailable = if (publicCatalog) true else it.catalogUnavailable,
                    sessionPhase = if (it.account == null) ApplicantSessionPhase.SIGNED_OUT else it.sessionPhase,
                    error = message)
            }
        }
    }

    private fun signOutWithError(title: UiMessage, detail: UiMessage) = mutate {
        ApplicantPortalState(
            apiBaseUrl = it.apiBaseUrl,
            recruitingCities = it.recruitingCities,
            error = ApplicantPortalMessage(title, detail),
        )
    }

    private fun fail(title: UiMessage, detail: UiMessage) = mutate {
        it.copy(busyLabel = null, sessionPhase = if (it.account == null) ApplicantSessionPhase.SIGNED_OUT else it.sessionPhase,
            error = ApplicantPortalMessage(title, detail))
    }

    private inline fun mutate(transform: (ApplicantPortalState) -> ApplicantPortalState) {
        mutableState.value = transform(mutableState.value)
    }
}

fun validateApplicantLogin(identifier: String, password: String): UiMessage? = when {
    identifier.trim().length < 3 -> UiMessage(Res.string.web_identifier_required)
    password.isEmpty() -> UiMessage(Res.string.web_password_required)
    password.length > 256 -> UiMessage(Res.string.web_password_too_long)
    else -> null
}

fun validateApplicantRegistration(
    displayName: String,
    email: String,
    phoneNumber: String,
    password: String,
): UiMessage? = when {
    displayName.isBlank() || displayName.trim().length > 120 -> UiMessage(Res.string.web_name_invalid)
    email.isBlank() && phoneNumber.isBlank() -> UiMessage(Res.string.web_contact_required)
    email.isNotBlank() && ('@' !in email || email.length > 320) -> UiMessage(Res.string.web_email_invalid)
    phoneNumber.length > 32 -> UiMessage(Res.string.web_phone_too_long)
    password.length !in 12..256 -> UiMessage(Res.string.web_password_registration_invalid)
    else -> null
}

internal fun applicantFailureMessage(error: Throwable, publicCatalog: Boolean): ApplicantPortalMessage {
    val detail = when {
        error is AuthenticationNetworkException -> Res.string.web_connection_unavailable
        error is ApiRequestException -> when (error.statusCode) {
            401 -> Res.string.web_session_detail
            403 -> Res.string.web_scope_denied
            404 -> Res.string.web_record_unavailable
            409 -> Res.string.web_record_changed
            422 -> Res.string.web_invalid_request
            429 -> Res.string.web_rate_limited
            503 -> if (publicCatalog) Res.string.web_catalog_unavailable else Res.string.web_service_unavailable
            else -> Res.string.web_request_unconfirmed
        }
        publicCatalog -> Res.string.web_catalog_unavailable
        else -> Res.string.web_request_unconfirmed
    }
    return ApplicantPortalMessage(UiMessage(Res.string.web_error_title), UiMessage(detail))
}
