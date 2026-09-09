package org.example.taximobile.applicant.state

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

data class ApplicantPortalMessage(val title: String, val detail: String)

data class ApplicantPortalState(
    val apiBaseUrl: String,
    val sessionPhase: ApplicantSessionPhase = ApplicantSessionPhase.SIGNED_OUT,
    val authMode: ApplicantAuthMode = ApplicantAuthMode.SIGN_IN,
    val account: CurrentAccount? = null,
    val recruitingCities: List<RecruitingCity> = emptyList(),
    val applications: List<DriverCityApplicationSummary> = emptyList(),
    val selectedApplication: DriverCityApplication? = null,
    val vehicles: List<DriverVehicle> = emptyList(),
    val credentials: List<DriverCredential> = emptyList(),
    val busyLabel: String? = null,
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
            fail("Check your sign-in details", validation)
            return
        }
        if (mutableState.value.interactionLocked) return
        scope.launch {
            mutate {
                it.copy(
                    sessionPhase = ApplicantSessionPhase.SIGNING_IN,
                    busyLabel = "Signing in",
                    error = null,
                    notice = null,
                )
            }
            try {
                when (val result = authentication.login(identifier.trim(), password, "Applicant web portal")) {
                    is AuthenticationState.Authenticated -> loadSignedIn(result.account)
                    is AuthenticationState.Failure -> signOutWithError(
                        "Sign-in failed",
                        "The credentials were rejected or the service could not be reached. Check them and try again.",
                    )
                    else -> signOutWithError("Sign-in failed", "The account session could not be established.")
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleFailure("Sign-in failed", error)
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
            fail("Check the account details", validation)
            return
        }
        if (mutableState.value.interactionLocked) return
        scope.launch {
            mutate { it.copy(busyLabel = "Creating account", error = null, notice = null) }
            try {
                when (
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
                                "Account created",
                                "Sign in with the email address or phone number you just registered.",
                            ),
                        )
                    }
                    is AuthenticationState.Failure -> fail(
                        "Account not created",
                        "The account details were rejected or the service could not be reached. Review them and try again.",
                    )
                    else -> fail("Account not created", "The registration response was not recognized.")
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleFailure("Account not created", error)
            }
        }
    }

    fun refresh() {
        val account = mutableState.value.account
        if (account == null) refreshCatalog() else launchBusy("Refreshing applications") { loadSignedIn(account) }
    }

    fun selectApplication(applicationId: String) = launchBusy("Loading application") {
        val application = recruitment.application(applicationId)
        reloadOwnedData(selected = application)
    }

    fun createApplication(cityId: String) = launchBusy("Starting city application") {
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
    ) = launchBusy("Saving application") {
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
                "Draft saved",
                "The backend confirmed application version ${application.optimisticVersion}.",
            ),
        )
    }

    fun submitApplication(applicationId: String) = launchBusy("Submitting for review") {
        val application = recruitment.submitApplication(applicationId)
        reloadOwnedData(
            selected = application,
            notice = ApplicantPortalMessage(
                "Application submitted",
                "${application.cityName.english} will review this city-scoped application.",
            ),
        )
    }

    fun withdrawApplication(applicationId: String) = launchBusy("Withdrawing application") {
        val application = recruitment.withdrawApplication(applicationId)
        reloadOwnedData(
            selected = application,
            notice = ApplicantPortalMessage(
                "Application withdrawn",
                "The record remains available. Your account and retained evidence were not deleted.",
            ),
        )
    }

    fun uploadDocument(
        applicationId: String,
        requirementItemId: String,
        expectedVersion: Int,
    ) = launchBusy("Choosing protected document") {
        val selected = pickBrowserDriverDocument() ?: return@launchBusy
        mutate { it.copy(busyLabel = "Scanning and saving document") }
        val application = recruitment.uploadDocument(
            applicationId,
            requirementItemId,
            expectedVersion,
            selected,
        )
        reloadOwnedData(
            selected = application,
            notice = ApplicantPortalMessage(
                "Document saved",
                "The backend scanned the file and confirmed application version " +
                    "${application.optimisticVersion}.",
            ),
        )
    }

    fun deleteDocument(
        applicationId: String,
        documentId: String,
        expectedVersion: Int,
    ) = launchBusy("Deleting protected document") {
        val application = recruitment.deleteDocument(
            applicationId,
            documentId,
            expectedVersion,
        )
        reloadOwnedData(
            selected = application,
            notice = ApplicantPortalMessage(
                "Document deleted",
                "The evidence was removed and the backend updated application completeness.",
            ),
        )
    }

    fun registerVehicle(vehicle: VehicleRegistration) = launchBusy("Registering vehicle") {
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
                    notice = ApplicantPortalMessage("Signed out", "The in-memory browser session was cleared."),
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
                mutate { it.copy(recruitingCities = cities, error = null) }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleFailure("Recruiting cities unavailable", error, keepSession = true)
            }
        }
    }

    private suspend fun loadSignedIn(account: CurrentAccount) {
        mutate {
            it.copy(
                sessionPhase = ApplicantSessionPhase.SIGNED_IN,
                account = account,
                busyLabel = "Loading your applications",
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
        val resolvedSelection = selected
            ?: applications.firstOrNull { it.id == selectedId }?.let { recruitment.application(it.id) }
            ?: applications.firstOrNull()?.let { recruitment.application(it.id) }
        val vehicles = if (applications.isEmpty()) emptyList() else driver.vehicles()
        val credentials = if (applications.isEmpty()) emptyList() else driver.credentials()
        mutate {
            it.copy(
                sessionPhase = ApplicantSessionPhase.SIGNED_IN,
                recruitingCities = cities,
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

    private fun launchBusy(label: String, command: suspend () -> Unit) {
        val current = mutableState.value
        if (current.sessionPhase != ApplicantSessionPhase.SIGNED_IN || current.interactionLocked) return
        scope.launch {
            mutate { it.copy(busyLabel = label, error = null, notice = null) }
            try {
                command()
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Throwable) {
                handleFailure("Application action failed", error)
            }
        }
    }

    private suspend fun handleFailure(title: String, error: Throwable, keepSession: Boolean = false) {
        when (error) {
            is AuthenticationRejectedException -> {
                authentication.logout()
                signOutWithError(
                    "Session expired",
                    "Sign in again before accessing an application.",
                )
            }
            is AuthenticationNetworkException -> fail(title, "The API could not be reached. Check the connection and try again.")
            is ApiRequestException -> fail(title, applicantApiError(error.statusCode))
            else -> if (keepSession) {
                fail(title, "The public catalog could not be loaded. Try again shortly.")
            } else {
                fail(title, "The request could not be completed. Refresh the record before trying again.")
            }
        }
    }

    private fun signOutWithError(title: String, detail: String) = mutate {
        ApplicantPortalState(
            apiBaseUrl = it.apiBaseUrl,
            recruitingCities = it.recruitingCities,
            error = ApplicantPortalMessage(title, detail),
        )
    }

    private fun fail(title: String, detail: String) = mutate {
        it.copy(busyLabel = null, sessionPhase = if (it.account == null) ApplicantSessionPhase.SIGNED_OUT else it.sessionPhase,
            error = ApplicantPortalMessage(title, detail))
    }

    private inline fun mutate(transform: (ApplicantPortalState) -> ApplicantPortalState) {
        mutableState.value = transform(mutableState.value)
    }
}

fun validateApplicantLogin(identifier: String, password: String): String? = when {
    identifier.trim().length < 3 -> "Enter the email address or phone number registered to the account."
    password.isEmpty() -> "Enter your password."
    password.length > 256 -> "The password is too long."
    else -> null
}

fun validateApplicantRegistration(
    displayName: String,
    email: String,
    phoneNumber: String,
    password: String,
): String? = when {
    displayName.isBlank() || displayName.trim().length > 120 -> "Enter a full name of up to 120 characters."
    email.isBlank() && phoneNumber.isBlank() -> "Provide an email address or Moroccan phone number."
    email.isNotBlank() && ('@' !in email || email.length > 320) -> "Enter a valid email address."
    phoneNumber.length > 32 -> "The phone number is too long."
    password.length !in 12..256 -> "Use a password between 12 and 256 characters."
    else -> null
}

private fun applicantApiError(statusCode: Int): String = when (statusCode) {
    401 -> "The browser session expired. Sign in again."
    404 -> "This record is unavailable or does not belong to the signed-in account."
    409 -> "The record changed or this action is no longer allowed. Refresh before trying again."
    422 -> "Some required information is missing or invalid. Review the highlighted requirements."
    429 -> "Too many requests were made. Wait briefly before trying again."
    503 -> "Protected document storage is unavailable. No file was accepted."
    else -> "The API rejected this request (HTTP $statusCode)."
}
