package org.example.taximobile.feature.app

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class AppActionTest {
    @Test
    fun gate_admits_one_action_and_rejects_duplicate_or_conflicting_work() {
        val gate = AppActionGate()
        val request = AppAction(AppActionKind.REQUEST_RIDE)

        assertTrue(gate.tryStart(request))
        assertEquals(request, gate.current)
        assertFalse(gate.tryStart(request))
        assertFalse(gate.tryStart(AppAction(AppActionKind.CANCEL_RIDE, "ride-1")))
    }

    @Test
    fun only_the_matching_completion_releases_the_gate() {
        val gate = AppActionGate()
        val selected = AppAction(AppActionKind.SELECT_DRIVER_VEHICLE, "vehicle-1")

        assertTrue(gate.tryStart(selected))
        gate.finish(AppAction(AppActionKind.SELECT_DRIVER_VEHICLE, "vehicle-2"))
        assertEquals(selected, gate.current)

        gate.finish(selected)
        assertNull(gate.current)
        assertTrue(gate.tryStart(AppAction(AppActionKind.UPDATE_DRIVER_LOCATION)))
    }

    @Test
    fun delayed_refresh_cannot_replace_a_newer_history_selection() {
        val gate = AppActionGate()
        val oldRefresh = gate.beginRead()
        val selected = AppAction(AppActionKind.LOAD_PASSENGER_RIDE, "recent-trip")

        assertTrue(gate.tryStart(selected))
        assertFalse(gate.canApplyRead(oldRefresh))
        val overlappingRefresh = gate.beginRead()
        assertFalse(gate.canApplyRead(overlappingRefresh))
        gate.finish(selected)
        assertFalse(gate.canApplyRead(oldRefresh))
        assertFalse(gate.canApplyRead(overlappingRefresh))
        assertTrue(gate.canApplyRead(gate.beginRead()))
    }

    @Test
    fun only_latest_passive_refresh_can_publish_and_auth_transition_invalidates_it() {
        val gate = AppActionGate()
        val slowRefresh = gate.beginRead()
        val fastRefresh = gate.beginRead()
        assertFalse(gate.canApplyRead(slowRefresh))
        assertTrue(gate.canApplyRead(fastRefresh))

        gate.invalidateReads()
        assertFalse(gate.canApplyRead(fastRefresh))
    }

    @Test
    fun pending_match_includes_the_resource_identity() {
        val pending = AppAction(AppActionKind.MARK_NOTIFICATION_READ, "notification-1")

        assertTrue(pending.isPending(AppActionKind.MARK_NOTIFICATION_READ, "notification-1"))
        assertFalse(pending.isPending(AppActionKind.MARK_NOTIFICATION_READ, "notification-2"))
        assertFalse(pending.isPending(AppActionKind.CREATE_SUPPORT_TICKET))
    }
}
