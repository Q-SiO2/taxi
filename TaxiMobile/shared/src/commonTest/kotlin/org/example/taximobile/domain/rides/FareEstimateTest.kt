package org.example.taximobile.domain.rides

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class FareEstimateTest {
    @Test
    fun `estimate retains backend tariff identity`() {
        val estimate = FareEstimate(amount = "35.00", currency = "MAD", pricingRuleVersion = "v1")

        assertEquals("35.00", estimate.amount)
        assertEquals("MAD", estimate.currency)
        assertEquals("v1", estimate.pricingRuleVersion)
    }
}

class RideRatingTest {
    @Test
    fun `rating has no participant identifiers in mobile presentation data`() {
        val rating = RideRating(id = "rating", score = 5, comment = null)

        assertEquals(5, rating.score)
        assertNull(rating.comment)
    }
}

class FinalRideFareTest {
    @Test
    fun `final fare remains a backend supplied amount and currency`() {
        val fare = FinalRideFare(amount = "35.00", currency = "MAD")

        assertEquals("35.00", fare.amount)
        assertEquals("MAD", fare.currency)
    }
}
