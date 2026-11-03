package org.example.taximobile.feature.maps

import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.v2.runComposeUiTest
import org.example.taximobile.domain.rides.Coordinates
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull

@OptIn(ExperimentalTestApi::class)
class MapCoordinateCallbackUiTest {
    @Test
    fun retained_native_listener_can_select_a_new_destination_after_a_trip_finishes() = runComposeUiTest {
        var activeTrip by mutableStateOf(true)
        var retainedListener: ((Coordinates) -> Unit)? = null
        val selected = mutableListOf<Coordinates>()
        val point = Coordinates(33.5731, -7.5898)
        setContent {
            val activeInThisComposition = activeTrip
            val listener = rememberMapCoordinateSelection { coordinate ->
                if (!activeInThisComposition) selected += coordinate
            }
            SideEffect { if (retainedListener == null) retainedListener = listener }
        }
        runOnIdle {
            assertNotNull(retainedListener)(point)
            assertEquals(emptyList(), selected)
            activeTrip = false
        }
        waitForIdle()
        runOnIdle { assertNotNull(retainedListener)(point) }
        assertEquals(listOf(point), selected, "A retained platform listener must see the current idle screen")
    }

    @Test
    fun retained_native_listener_cannot_select_points_after_a_trip_becomes_active() = runComposeUiTest {
        var activeTrip by mutableStateOf(false)
        var retainedListener: ((Coordinates) -> Unit)? = null
        val selected = mutableListOf<Coordinates>()
        val point = Coordinates(33.5731, -7.5898)
        setContent {
            val activeInThisComposition = activeTrip
            val listener = rememberMapCoordinateSelection { coordinate ->
                if (!activeInThisComposition) selected += coordinate
            }
            SideEffect { if (retainedListener == null) retainedListener = listener }
        }
        runOnIdle {
            assertNotNull(retainedListener)(point)
            activeTrip = true
        }
        waitForIdle()
        runOnIdle { assertNotNull(retainedListener)(point) }
        assertEquals(listOf(point), selected, "A retained listener must preserve the current active-trip selection guard")
    }
}
