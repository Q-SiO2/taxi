package org.example.taximobile.feature.location

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class OneShotLocationGateTest {
    @Test
    fun repeated_request_is_rejected_until_the_active_request_finishes() {
        val gate = OneShotLocationGate()

        assertTrue(gate.tryStart())
        assertTrue(gate.inFlight)
        assertFalse(gate.tryStart())

        gate.finish()

        assertFalse(gate.inFlight)
        assertTrue(gate.tryStart())
    }
}
