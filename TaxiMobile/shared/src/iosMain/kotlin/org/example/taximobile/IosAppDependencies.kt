package org.example.taximobile

import io.ktor.client.HttpClient
import io.ktor.client.engine.darwin.Darwin
import org.example.taximobile.app.AppRole
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.auth.IosSecureTokenStore
import org.example.taximobile.data.auth.KtorAuthenticationGateway
import org.example.taximobile.data.drivers.KtorDriverGateway
import org.example.taximobile.data.drivers.KtorDriverOfferGateway
import org.example.taximobile.data.drivers.KtorDriverRideGateway
import org.example.taximobile.data.network.configureTaxiMobileTransport
import org.example.taximobile.data.realtime.KtorLiveEventGateway
import org.example.taximobile.data.rides.KtorRideGateway
import org.example.taximobile.data.passengers.KtorPassengerProfileGateway
import org.example.taximobile.data.support.KtorSupportGateway
import org.example.taximobile.data.notifications.KtorNotificationGateway
import org.example.taximobile.data.routing.KtorRoutingGateway
import org.example.taximobile.data.cooperatives.KtorCooperativeGateway
import org.example.taximobile.feature.app.MobileAppCoordinator
import org.example.taximobile.feature.auth.AuthenticationSessionCoordinator
import platform.Foundation.NSLocale

/** iOS composition root mirrors Android while retaining native storage/transport. */
class IosAppDependencies(apiBaseUrl: String, role: AppRole) {
    private val client = HttpClient(Darwin) { configureTaxiMobileTransport() }
    private val tokens = IosSecureTokenStore()
    private val api = ApiConfiguration(apiBaseUrl)
    private val authentication = KtorAuthenticationGateway(client = client, api = api)

    val appCoordinator = MobileAppCoordinator(
        appRole = role,
        authentication = AuthenticationSessionCoordinator(authentication, tokens),
        driver = KtorDriverGateway(client, api) {
            tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException()
        },
        driverOffers = KtorDriverOfferGateway(client, api) {
            tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException()
        },
        driverRides = KtorDriverRideGateway(client, api) {
            tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException()
        },
        rides = KtorRideGateway(client, api) {
            tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException()
        },
        passengerProfile = KtorPassengerProfileGateway(client, api) {
            tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException()
        },
        support = KtorSupportGateway(client, api) {
            tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException()
        },
        notifications = KtorNotificationGateway(client, api) {
            tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException()
        },
        liveEvents = KtorLiveEventGateway(client, api) {
            tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException()
        },
        routing = KtorRoutingGateway(
            client = client,
            api = api,
            accessToken = { tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException() },
            language = { NSLocale.preferredLanguages.firstOrNull()?.toString() ?: "en" },
        ),
        cooperatives = KtorCooperativeGateway(client, api) {
            tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException()
        },
    )
}
