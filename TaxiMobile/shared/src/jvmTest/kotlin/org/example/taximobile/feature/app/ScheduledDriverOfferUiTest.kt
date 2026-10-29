package org.example.taximobile.feature.app

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.*
import androidx.compose.ui.test.v2.runComposeUiTest
import org.example.taximobile.App
import org.example.taximobile.app.AppRole
import org.example.taximobile.data.scheduling.scheduledOfferFixture
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.time.TestTimeSource
import kotlin.time.Duration.Companion.seconds
import org.example.taximobile.feature.ui.theme.TaxiStyle
import org.example.taximobile.feature.ui.theme.TaxiStylePreferences
import org.example.taximobile.feature.ui.theme.TaxiStyleStore
import java.util.Locale

@OptIn(ExperimentalTestApi::class, kotlin.time.ExperimentalTime::class)
class ScheduledDriverOfferUiTest {
    @Test fun unknown_refund_terms_are_unavailable_and_accept_is_disabled() = runComposeUiTest {
        val offer = scheduledOfferFixture().let { it.copy(cancellationTerms = it.cancellationTerms.copy(surchargeRefundMode = "FUTURE_PRIVATE_POLICY", summary = "Guaranteed refund PRIVATE")) }
        var commands = 0
        setContent { App(appRole = AppRole.DRIVER, state = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE, scheduledOffers = listOf(offer)),
            onRespondToScheduledOffer = { _, _ -> commands++ }) }
        onNodeWithText("Scheduled work (1 offers · 0 commitments)").performScrollTo().performClick()
        onNodeWithText("Cancellation terms unavailable. Refresh or update the app before confirming.").performScrollTo().assertIsDisplayed()
        onNodeWithText("Accept commitment").performScrollTo().assertIsNotEnabled()
        onAllNodesWithText("Guaranteed refund PRIVATE").assertCountEquals(0)
        assertEquals(0, commands)
    }

    @Test fun expired_response_cannot_be_accepted() = runComposeUiTest {
        val offer = scheduledOfferFixture().copy(expiresAt = "2026-11-01T07:59:00Z")
        setContent { App(appRole = AppRole.DRIVER, state = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE, scheduledOffers = listOf(offer))) }
        onNodeWithText("Scheduled work (1 offers · 0 commitments)").performScrollTo().performClick()
        onNodeWithText("Accept commitment").performScrollTo().assertIsNotEnabled()
    }

    @Test fun invalid_response_timing_cannot_be_accepted() = runComposeUiTest {
        val offer = scheduledOfferFixture().copy(serverTime = "PRIVATE-invalid")
        setContent { App(appRole = AppRole.DRIVER, state = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE, scheduledOffers = listOf(offer))) }
        onNodeWithText("Scheduled work (1 offers · 0 commitments)").performScrollTo().performClick()
        onNodeWithText("Accept commitment").performScrollTo().assertIsNotEnabled()
    }

    @Test fun a_current_known_offer_sends_only_the_explicit_selected_acceptance() = runComposeUiTest {
        val actions = mutableListOf<Pair<String,Boolean>>()
        val offer = scheduledOfferFixture()
        setContent { App(appRole = AppRole.DRIVER, state = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE, scheduledOffers = listOf(offer)),
            onRespondToScheduledOffer = { id, accept -> actions += id to accept }) }
        onNodeWithText("Scheduled work (1 offers · 0 commitments)").performScrollTo().performClick()
        assertEquals(emptyList(),actions)
        onNodeWithText("Accept commitment").performScrollTo().performClick()
        assertEquals(listOf("offer-synthetic" to true),actions)
    }

    @Test fun unsupported_acceptance_remains_disabled_but_decline_is_explicit_in_every_language_and_style() {
        val original = Locale.getDefault()
        try {
            for ((language, navigation, accept, decline, unavailable) in listOf(
                listOf("en","Scheduled work","Accept commitment","Decline","Cancellation terms unavailable. Refresh or update the app before confirming."),
                listOf("fr","Travail planifié","Accepter l’engagement","Refuser","Conditions d’annulation indisponibles. Actualisez ou mettez l’application à jour avant de confirmer."),
                listOf("ar","العمل المجدول","قبول الالتزام","رفض","شروط الإلغاء غير متاحة. حدّث البيانات أو التطبيق قبل التأكيد."),
            )) {
                Locale.setDefault(Locale.forLanguageTag(language))
                for (style in TaxiStyle.entries) {
                    val offer = scheduledOfferFixture().let { it.copy(cancellationTerms = it.cancellationTerms.copy(surchargeRefundMode = "FUTURE_PRIVATE_POLICY")) }
                    val preferences = TaxiStylePreferences(object : TaxiStyleStore {
                        override fun read() = style.storageValue
                        override fun write(value: String) = Unit
                    })
                    runComposeUiTest {
                        val actions = mutableListOf<Pair<String,Boolean>>()
                        setContent { App(appRole = AppRole.DRIVER, state = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE,scheduledOffers = listOf(offer)),stylePreferences = preferences,
                            onRespondToScheduledOffer = { id,accepted -> actions += id to accepted }) }
                        onNodeWithText(navigation,substring = true).performScrollTo().performClick()
                        onNodeWithText(unavailable).performScrollTo().assertIsDisplayed()
                        onNodeWithText(accept).performScrollTo().assertIsNotEnabled()
                        onNodeWithText(decline).performScrollTo().performClick()
                        assertEquals(listOf(offer.id to false),actions)
                    }
                }
            }
        } finally { Locale.setDefault(original) }
    }

    @Test fun elapsed_time_and_repeated_invalid_readback_refresh_once_without_a_business_command() = runComposeUiTest {
        val clock = TestTimeSource()
        val offer = mutableStateOf(scheduledOfferFixture(clock.markNow()))
        var refreshes = 0
        var commands = 0
        setContent { App(appRole = AppRole.DRIVER,state = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE,scheduledOffers = listOf(offer.value)),
            onRefresh = { refreshes++ },onRespondToScheduledOffer = { _,_ -> commands++ }) }
        onNodeWithText("Scheduled work",substring = true).performScrollTo().performClick()
        onNodeWithText("Accept commitment").performScrollTo().assertIsEnabled()
        runOnIdle { clock += 61.seconds }
        mainClock.advanceTimeBy(500)
        waitForIdle()
        onNodeWithText("Accept commitment").assertIsNotEnabled()
        assertEquals(1,refreshes)
        runOnIdle { offer.value = offer.value.copy(serverTime = "PRIVATE-invalid",readStartedAt = clock.markNow()) }
        waitForIdle()
        assertEquals(1,refreshes)
        onNodeWithText("Refresh scheduled work").performScrollTo().performClick()
        assertEquals(2,refreshes)
        assertEquals(0,commands)
    }

    @Test fun pending_refresh_keeps_its_accessible_purpose_and_disables_acceptance() = runComposeUiTest {
        val pending = mutableStateOf<AppAction?>(null)
        val offer = scheduledOfferFixture()
        var refreshes = 0
        setContent { App(appRole = AppRole.DRIVER,state = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE,scheduledOffers = listOf(offer)),
            pendingAction = pending.value,onRefresh = { refreshes++ }) }
        onNodeWithText("Scheduled work",substring = true).performScrollTo().performClick()
        runOnIdle { pending.value = AppAction(AppActionKind.REFRESH) }
        onNodeWithContentDescription("Refresh scheduled work").performScrollTo().assertIsNotEnabled()
        onNodeWithText("Accept commitment").performScrollTo().assertIsNotEnabled()
        assertEquals(0,refreshes)
    }
}
