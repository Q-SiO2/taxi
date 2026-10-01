package org.example.taximobile.feature.passenger

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextReplacement
import androidx.compose.ui.test.v2.runComposeUiTest
import kotlin.test.Test
import kotlin.test.assertEquals
import org.example.taximobile.domain.places.PlaceAttribution
import org.example.taximobile.domain.places.PlaceKind
import org.example.taximobile.domain.places.PlaceResult
import org.example.taximobile.domain.places.PlaceSearch
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.LocalizedText
import org.example.taximobile.domain.rides.PublicRideCity
import org.example.taximobile.feature.app.PlaceDiscoveryUiState
import org.example.taximobile.feature.ui.theme.TaxiTheme

@OptIn(ExperimentalTestApi::class)
class PlaceDiscoveryFreshnessUiTest {
    private fun city(id: String) = PublicRideCity(
        id, id, LocalizedText(id, id, id), "Africa/Casablanca", "PILOT", true,
    )

    private fun discovery(cityId: String, query: String, resultId: String) = PlaceDiscoveryUiState(
        search = PlaceSearch(
            cityId, query,
            listOf(PlaceResult(resultId, resultId, null, Coordinates(34.02, -6.84), PlaceKind.POI, true)),
            PlaceAttribution("OpenStreetMap", "https://www.openstreetmap.org/copyright"),
        ),
    )

    @Test
    fun edited_query_hides_old_and_late_results_until_matching_response_arrives() = runComposeUiTest {
        var state by mutableStateOf(discovery("rabat", "Gare", "old"))
        var selected: PlaceResult? = null
        setContent {
            TaxiTheme {
                PlaceDiscoverySection(listOf(city("rabat")), "rabat", state, true, null,
                    onSelectCity = {}, onSearch = { _, _ -> }, onSelectResult = { selected = it })
            }
        }
        onNodeWithTag("place-result-old").assertIsDisplayed()
        onNodeWithTag("place-search-query").performTextReplacement("Airport")
        onNodeWithTag("place-result-old").assertDoesNotExist()
        runOnIdle { state = discovery("rabat", "Gare", "late") }
        onNodeWithTag("place-result-late").assertDoesNotExist()
        runOnIdle { state = discovery("rabat", "Airport", "current") }
        onNodeWithTag("place-result-current").assertIsDisplayed().performClick()
        runOnIdle { assertEquals("current", selected?.id) }
    }

    @Test
    fun empty_and_short_query_never_expose_a_previous_result() = runComposeUiTest {
        setContent {
            TaxiTheme {
                PlaceDiscoverySection(listOf(city("rabat")), "rabat", discovery("rabat", "Gare", "old"),
                    true, null, onSelectCity = {}, onSearch = { _, _ -> }, onSelectResult = {})
            }
        }
        onNodeWithTag("place-search-query").performTextReplacement("")
        onNodeWithTag("place-result-old").assertDoesNotExist()
        onNodeWithTag("place-search-query").performTextReplacement("G")
        onNodeWithTag("place-result-old").assertDoesNotExist()
    }

    @Test
    fun city_change_hides_a_matching_query_from_the_previous_city() = runComposeUiTest {
        var selectedCity by mutableStateOf("rabat")
        var state by mutableStateOf(discovery("rabat", "Gare", "old"))
        setContent {
            TaxiTheme {
                PlaceDiscoverySection(listOf(city(selectedCity)), selectedCity, state, true, null,
                    onSelectCity = {}, onSearch = { _, _ -> }, onSelectResult = {})
            }
        }
        onNodeWithTag("place-result-old").assertIsDisplayed()
        runOnIdle { selectedCity = "casablanca" }
        onNodeWithTag("place-result-old").assertDoesNotExist()
        runOnIdle { state = discovery("casablanca", "Gare", "current") }
        onNodeWithTag("place-result-current").assertIsDisplayed()
    }
}
