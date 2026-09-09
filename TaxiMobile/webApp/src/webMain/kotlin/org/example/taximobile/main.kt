package org.example.taximobile

import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.window.ComposeViewport
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import io.ktor.client.HttpClient
import io.ktor.client.engine.js.Js
import kotlin.js.ExperimentalWasmJsInterop
import kotlinx.browser.document
import kotlinx.browser.window
import org.example.taximobile.applicant.state.ApplicantPortalCoordinator
import org.example.taximobile.applicant.state.InMemoryApplicantTokenStore
import org.example.taximobile.applicant.ui.ApplicantPortalApp
import org.example.taximobile.application.OperationsEnvironment
import org.example.taximobile.application.WebSurface
import org.example.taximobile.application.selectWebSurface
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.KtorAuthenticationGateway
import org.example.taximobile.data.drivers.KtorDriverGateway
import org.example.taximobile.data.drivers.KtorDriverRecruitmentGateway
import org.example.taximobile.data.network.configureTaxiMobileTransport
import org.example.taximobile.feature.auth.AuthenticationSessionCoordinator
import org.example.taximobile.operations.data.KtorOperationsGateway
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.ui.OperationsApp
import web.http.RequestCredentials
import web.http.include

@OptIn(ExperimentalComposeUiApi::class, ExperimentalWasmJsInterop::class)
fun main() {
    val initialSurface = selectWebSurface(window.location.pathname, window.location.hash)
    document.title = if (initialSurface == WebSurface.APPLICANT) {
        "TaxiMobile Driver Applications"
    } else {
        "TaxiMobile Operations"
    }
    document.getElementById("boot-status")?.remove()
    ComposeViewport {
        val environment = remember { OperationsEnvironment.fromBrowser() }
        val api = remember(environment) {
            ApiConfiguration(environment.apiBaseUrl.removeSuffix("/api/v1"))
        }
        val client = remember {
            HttpClient(Js) {
                engine {
                    configureRequest { credentials = RequestCredentials.include }
                }
                configureTaxiMobileTransport()
            }
        }
        val coroutineScope = rememberCoroutineScope()
        val surface = remember { initialSurface }
        DisposableEffect(client) {
            onDispose { client.close() }
        }
        when (surface) {
            WebSurface.OPERATIONS -> {
                val coordinator = remember(client, environment, coroutineScope) {
                    OperationsCoordinator(
                        gateway = KtorOperationsGateway(client, environment.apiBaseUrl),
                        scope = coroutineScope,
                        apiBaseUrl = environment.apiBaseUrl,
                        isLocalDevelopment = environment.isLocalDevelopment,
                    )
                }
                OperationsApp(coordinator)
            }
            WebSurface.APPLICANT -> {
                val coordinator = remember(client, environment, coroutineScope) {
                    val tokenStore = InMemoryApplicantTokenStore()
                    ApplicantPortalCoordinator(
                        authentication = AuthenticationSessionCoordinator(
                            gateway = KtorAuthenticationGateway(client, api),
                            tokenStore = tokenStore,
                        ),
                        recruitment = KtorDriverRecruitmentGateway(client, api, tokenStore::accessToken),
                        driver = KtorDriverGateway(client, api, tokenStore::accessToken),
                        scope = coroutineScope,
                        apiBaseUrl = environment.apiBaseUrl,
                    )
                }
                ApplicantPortalApp(coordinator)
            }
        }
    }
}
