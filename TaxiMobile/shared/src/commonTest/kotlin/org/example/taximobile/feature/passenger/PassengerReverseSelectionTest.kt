package org.example.taximobile.feature.passenger

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import org.example.taximobile.domain.places.PlaceKind
import org.example.taximobile.domain.places.PlaceResult
import org.example.taximobile.domain.rides.Coordinates

class PassengerReverseSelectionTest {
    private val original = Coordinates(34.0209, -6.8416)
    private val moved = Coordinates(34.03, -6.85, "New selection")

    private fun result(coordinate: Coordinates) = PlaceResult(
        "result", "Station", "Rabat", coordinate, PlaceKind.POI, true,
    )

    private fun select(form: PassengerTripFormState, target: MapSelectionTarget, point: Coordinates) {
        form.selectionTarget = target
        form.select(point)
    }

    @Test
    fun reverse_lookup_only_adds_a_label_to_the_existing_point() {
        for (target in MapSelectionTarget.entries) {
            val form = PassengerTripFormState()
            select(form, target, original)
            assertTrue(form.applyReverseAddress(target, result(original)))
            val point = if (target == MapSelectionTarget.Pickup) form.pickup else form.destination
            assertEquals(original.copy(address = "Station, Rabat"), point)
        }
    }

    @Test
    fun late_reverse_result_cannot_move_or_relabel_a_new_selection() {
        for (target in MapSelectionTarget.entries) {
            val form = PassengerTripFormState()
            select(form, target, original)
            select(form, target, moved)
            assertFalse(form.matchesSelectedPoint(target, original))
            assertFalse(form.applyReverseAddress(target, result(original)))
            assertEquals(moved, if (target == MapSelectionTarget.Pickup) form.pickup else form.destination)
        }
    }

    @Test
    fun missing_or_invalid_selection_cannot_be_created_by_reverse_lookup() {
        val form = PassengerTripFormState()
        assertFalse(form.applyReverseAddress(MapSelectionTarget.Pickup, result(original)))
        select(form, MapSelectionTarget.Pickup, original)
        form.updatePickupLatitude("invalid")
        assertFalse(form.matchesSelectedPoint(MapSelectionTarget.Pickup, original))
        assertFalse(form.applyReverseAddress(MapSelectionTarget.Pickup, result(original)))
        assertEquals("invalid", form.pickupLatitude)
    }

    @Test
    fun reverse_lookup_for_one_target_does_not_change_the_other() {
        val form = PassengerTripFormState()
        select(form, MapSelectionTarget.Pickup, original)
        select(form, MapSelectionTarget.Destination, moved)
        assertTrue(form.applyReverseAddress(MapSelectionTarget.Pickup, result(original)))
        assertEquals(moved, form.destination)
        assertTrue(form.matchesSelectedPoint(MapSelectionTarget.Pickup, original.copy(address = "ignored")))
    }
}
