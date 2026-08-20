package org.example.taximobile.domain.drivers

import kotlin.test.Test
import kotlin.test.assertEquals

class DriverEarningsTest {
    @Test
    fun `earnings render backend supplied exact amounts without client arithmetic`() {
        val earnings = DriverEarnings(
            "MAD",
            "35.00",
            "0.00",
            "0.00",
            "35.00",
            settledThrough = "2026-08-13T12:00:00Z",
            count = 1,
            items = listOf(
                DriverEarningItem(
                    "earning",
                    "ride",
                    "35.00",
                    "0.00",
                    "0.00",
                    "35.00",
                    "MAD",
                    "2026-08-13T12:00:00Z",
                )
            ),
        )

        assertEquals("35.00", earnings.net)
        assertEquals(1, earnings.count)
        assertEquals("ride", earnings.items.single().rideId)
    }
}
