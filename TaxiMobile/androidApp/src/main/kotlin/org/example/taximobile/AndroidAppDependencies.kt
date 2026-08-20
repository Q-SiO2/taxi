package org.example.taximobile

import android.content.Context
import io.ktor.client.HttpClient
import io.ktor.client.engine.okhttp.OkHttp
import org.example.taximobile.app.AppRole
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AndroidSecureTokenStore
import org.example.taximobile.data.auth.KtorAuthenticationGateway
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.drivers.KtorDriverGateway
import org.example.taximobile.data.drivers.KtorDriverOfferGateway
import org.example.taximobile.data.drivers.KtorDriverRideGateway
import org.example.taximobile.data.rides.KtorRideGateway
import org.example.taximobile.data.passengers.KtorPassengerProfileGateway
import org.example.taximobile.data.support.KtorSupportGateway
import org.example.taximobile.data.realtime.KtorLiveEventGateway
import org.example.taximobile.data.notifications.KtorNotificationGateway
import org.example.taximobile.data.routing.KtorRoutingGateway
import org.example.taximobile.data.network.configureTaxiMobileTransport
import org.example.taximobile.data.cooperatives.KtorCooperativeGateway
import org.example.taximobile.feature.app.MobileAppCoordinator
import org.example.taximobile.feature.auth.AuthenticationSessionCoordinator
import java.util.Locale

class AndroidAppDependencies(context: Context, role: AppRole) {
    private val client = HttpClient(OkHttp) { configureTaxiMobileTransport() }
    private val tokens = AndroidSecureTokenStore(context.applicationContext)
    private val authentication = KtorAuthenticationGateway(
        client = client,
        api = ApiConfiguration(BuildConfig.API_BASE_URL),
    )

    val appCoordinator = MobileAppCoordinator(
        appRole = role,
        authentication = AuthenticationSessionCoordinator(authentication, tokens),
        driver = KtorDriverGateway(
            client = client,
            api = ApiConfiguration(BuildConfig.API_BASE_URL),
            accessToken = { tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException() },
        ),
        driverOffers = KtorDriverOfferGateway(
            client = client,
            api = ApiConfiguration(BuildConfig.API_BASE_URL),
            accessToken = { tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException() },
        ),
        driverRides = KtorDriverRideGateway(
            client = client,
            api = ApiConfiguration(BuildConfig.API_BASE_URL),
            accessToken = { tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException() },
        ),
        rides = KtorRideGateway(
            client = client,
            api = ApiConfiguration(BuildConfig.API_BASE_URL),
            accessToken = { tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException() },
        ),
        passengerProfile = KtorPassengerProfileGateway(
            client = client,
            api = ApiConfiguration(BuildConfig.API_BASE_URL),
            accessToken = { tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException() },
        ),
        support = KtorSupportGateway(
            client = client,
            api = ApiConfiguration(BuildConfig.API_BASE_URL),
            accessToken = { tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException() },
        ),
        notifications = KtorNotificationGateway(client, ApiConfiguration(BuildConfig.API_BASE_URL)) {
            tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException()
        },
        liveEvents = KtorLiveEventGateway(
            client = client,
            api = ApiConfiguration(BuildConfig.API_BASE_URL),
            accessToken = { tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException() },
        ),
        routing = KtorRoutingGateway(
            client = client,
            api = ApiConfiguration(BuildConfig.API_BASE_URL),
            accessToken = { tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException() },
            language = { Locale.getDefault().toLanguageTag() },
        ),
        cooperatives = KtorCooperativeGateway(
            client = client,
            api = ApiConfiguration(BuildConfig.API_BASE_URL),
            accessToken = { tokens.tokens()?.accessToken ?: throw AuthenticationRejectedException() },
        ),
    )
}
