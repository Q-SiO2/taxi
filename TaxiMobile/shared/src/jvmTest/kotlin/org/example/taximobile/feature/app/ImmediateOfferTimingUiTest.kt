package org.example.taximobile.feature.app

import androidx.compose.ui.test.*
import androidx.compose.ui.test.v2.runComposeUiTest
import org.example.taximobile.App
import org.example.taximobile.app.AppRole
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.drivers.DriverRideOffer
import org.example.taximobile.domain.rides.Coordinates
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.time.TestTimeSource
import kotlin.time.Duration.Companion.seconds
import androidx.compose.runtime.mutableStateOf
import org.example.taximobile.domain.rides.RideServiceType
import org.example.taximobile.feature.ui.theme.TaxiStyle
import org.example.taximobile.feature.ui.theme.TaxiStylePreferences
import org.example.taximobile.feature.ui.theme.TaxiStyleStore
import java.util.Locale

internal fun immediateOfferFixture() = DriverRideOffer(
    id="synthetic-immediate",rideId="synthetic-ride",pickup=Coordinates(34.03,-5.00),
    issuedAt="2026-11-01T08:00:00Z",expiresAt="2026-11-01T08:01:00Z",serverTimeAtFetch="2026-11-01T08:00:00Z",
)

@OptIn(ExperimentalTestApi::class,kotlin.time.ExperimentalTime::class)
class ImmediateOfferTimingUiTest {
    @Test fun elapsed_time_without_timer_callbacks_cannot_keep_acceptance_enabled() = runComposeUiTest {
        val clock=TestTimeSource()
        val offer=immediateOfferFixture().copy(readStartedAt=clock.markNow())
        var actions=0
        setContent { App(appRole=AppRole.DRIVER,state=AppUiState.DriverReady(DriverAvailabilityStatus.AVAILABLE,offers=listOf(offer)),
            onRespondToOffer={_,_->actions++}) }
        onNodeWithText("Accept").performScrollTo()
        mainClock.autoAdvance=false
        // Advance elapsed time independently of UI timer callbacks.
        runOnIdle {clock+=61.seconds}
        mainClock.advanceTimeBy(500)
        onNodeWithText("Accept").assertIsNotEnabled()
        assertEquals(0,actions)
    }

    @Test fun current_known_offer_remains_an_explicit_single_acceptance() = runComposeUiTest {
        val offer=immediateOfferFixture()
        val actions=mutableListOf<Pair<String,Boolean>>()
        setContent { App(appRole=AppRole.DRIVER,state=AppUiState.DriverReady(DriverAvailabilityStatus.AVAILABLE,offers=listOf(offer)),
            onRespondToOffer={id,accept->actions+=id to accept}) }
        assertEquals(emptyList(),actions)
        onNodeWithText("Accept").performScrollTo().performClick()
        assertEquals(listOf(offer.id to true),actions)
    }

    @Test fun reopening_the_card_cannot_restart_its_window()=runComposeUiTest {
        val clock=TestTimeSource()
        val offer=immediateOfferFixture().copy(readStartedAt=clock.markNow())
        val visible=mutableStateOf(true)
        var actions=0
        setContent {if(visible.value) App(appRole=AppRole.DRIVER,state=AppUiState.DriverReady(DriverAvailabilityStatus.AVAILABLE,offers=listOf(offer)),
            onRespondToOffer={_,_->actions++})}
        onNodeWithText("Accept").performScrollTo().assertIsEnabled()
        runOnIdle{visible.value=false;clock+=61.seconds}
        waitForIdle()
        runOnIdle{visible.value=true}
        onNodeWithText("Accept").performScrollTo().assertIsNotEnabled()
        assertEquals(0,actions)
    }

    @Test fun repeated_invalid_envelopes_auto_refresh_once_and_explicit_retry_retains_its_purpose()=runComposeUiTest {
        val clock=TestTimeSource()
        val offer=mutableStateOf(immediateOfferFixture().copy(serverTimeAtFetch="PRIVATE-invalid",readStartedAt=clock.markNow()))
        val pending=mutableStateOf<AppAction?>(null)
        var refreshes=0
        var actions=0
        setContent {App(appRole=AppRole.DRIVER,state=AppUiState.DriverReady(DriverAvailabilityStatus.AVAILABLE,offers=listOf(offer.value)),pendingAction=pending.value,
            onRefresh={refreshes++},onRespondToOffer={_,_->actions++})}
        onNodeWithText("Accept").performScrollTo().assertIsNotEnabled()
        assertEquals(1,refreshes)
        runOnIdle{clock+=1.seconds;offer.value=offer.value.copy(readStartedAt=clock.markNow())}
        waitForIdle()
        assertEquals(1,refreshes)
        onNodeWithText("Refresh offers").performScrollTo().performClick()
        assertEquals(2,refreshes)
        runOnIdle{pending.value=AppAction(AppActionKind.REFRESH)}
        onNodeWithContentDescription("Refresh offers").performScrollTo().assertIsNotEnabled()
        assertEquals(0,actions)
    }

    @Test fun unsupported_service_does_not_become_an_on_demand_acceptance()=runComposeUiTest {
        val offer=immediateOfferFixture().copy(serviceType=RideServiceType.UNKNOWN)
        var actions=0
        setContent {App(appRole=AppRole.DRIVER,state=AppUiState.DriverReady(DriverAvailabilityStatus.AVAILABLE,offers=listOf(offer)),
            onRespondToOffer={_,_->actions++})}
        onNodeWithText("Service unavailable").performScrollTo().assertIsDisplayed()
        onNodeWithText("Accept").performScrollTo().assertIsNotEnabled()
        onNodeWithText("Refresh offers").performScrollTo().assertIsEnabled()
        assertEquals(0,actions)
    }

    @Test fun unsupported_service_can_still_be_explicitly_declined_after_confirmation()=runComposeUiTest {
        val offer=immediateOfferFixture().copy(serviceType=RideServiceType.UNKNOWN)
        val actions=mutableListOf<Pair<String,Boolean>>()
        setContent{App(appRole=AppRole.DRIVER,state=AppUiState.DriverReady(DriverAvailabilityStatus.AVAILABLE,offers=listOf(offer)),
            onRespondToOffer={id,accept->actions+=id to accept})}
        onNodeWithText("Decline").performScrollTo().performClick()
        assertEquals(emptyList(),actions)
        onNodeWithText("Decline offer").performClick()
        assertEquals(listOf(offer.id to false),actions)
    }

    @Test fun pending_acceptance_retains_accessible_purpose_and_blocks_a_second_action()=runComposeUiTest {
        val offer=immediateOfferFixture()
        val pending=mutableStateOf<AppAction?>(null)
        val actions=mutableListOf<Pair<String,Boolean>>()
        setContent{App(appRole=AppRole.DRIVER,state=AppUiState.DriverReady(DriverAvailabilityStatus.AVAILABLE,offers=listOf(offer)),pendingAction=pending.value,
            onRespondToOffer={id,accept->actions+=id to accept;pending.value=AppAction(AppActionKind.RESPOND_TO_OFFER,"$id:accept")})}
        onNodeWithText("Accept").performScrollTo().performClick()
        onNodeWithContentDescription("Accept").performScrollTo().assertIsNotEnabled()
        onNodeWithContentDescription("Decline").performScrollTo().assertIsNotEnabled()
        assertEquals(listOf(offer.id to true),actions)
    }

    @Test fun expired_offer_review_and_explicit_refresh_work_in_each_language_and_style(){
        val original=Locale.getDefault()
        try{
            for((language,accept,refresh)in listOf(listOf("en","Accept","Refresh offers"),listOf("fr","Accepter","Actualiser les offres"),listOf("ar","قبول","تحديث العروض"))){
                Locale.setDefault(Locale.forLanguageTag(language))
                for(style in TaxiStyle.entries){
                    val offer=immediateOfferFixture().let{it.copy(expiresAt=it.serverTimeAtFetch)}
                    val preferences=TaxiStylePreferences(object:TaxiStyleStore{
                        override fun read()=style.storageValue
                        override fun write(value:String)=Unit
                    })
                    runComposeUiTest{
                        var refreshes=0
                        var actions=0
                        setContent{App(appRole=AppRole.DRIVER,state=AppUiState.DriverReady(DriverAvailabilityStatus.AVAILABLE,offers=listOf(offer)),stylePreferences=preferences,
                            onRefresh={refreshes++},onRespondToOffer={_,_->actions++})}
                        onNodeWithText(accept).performScrollTo().assertIsNotEnabled()
                        assertEquals(1,refreshes)
                        onNodeWithText(refresh).performScrollTo().performClick()
                        assertEquals(2,refreshes)
                        assertEquals(0,actions)
                    }
                }
            }
        }finally{Locale.setDefault(original)}
    }
}
