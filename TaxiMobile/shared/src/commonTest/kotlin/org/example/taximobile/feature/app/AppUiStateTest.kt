package org.example.taximobile.feature.app

import kotlin.test.Test
import kotlin.test.assertEquals
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.support.SupportCategory
import taximobile.shared.generated.resources.*

class AppUiStateTest {
    @Test
    fun `passenger labels derive from backend ride status`() {
        assertEquals(Res.string.ride_status_matching, RideStatus.MATCHING.passengerStatusResource())
        assertEquals(Res.string.ride_status_in_progress, RideStatus.IN_PROGRESS.passengerStatusResource())
        assertEquals(Res.string.ride_status_unmatched, RideStatus.UNMATCHED.passengerStatusResource())
    }
}

class SupportCategoryTest {
    @Test
    fun `support categories are controlled values rather than free text`() {
        assertEquals(SupportCategory.FARE_DISPUTE, SupportCategory.valueOf("FARE_DISPUTE"))
    }
}
