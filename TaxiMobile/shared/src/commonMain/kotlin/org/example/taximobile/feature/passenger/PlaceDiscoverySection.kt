package org.example.taximobile.feature.passenger

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.input.ImeAction
import kotlinx.coroutines.delay
import org.example.taximobile.domain.places.PlaceKind
import org.example.taximobile.domain.places.PlaceResult
import org.example.taximobile.domain.rides.PublicRideCity
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.PlaceDiscoveryUiState
import org.example.taximobile.feature.app.isPending
import org.example.taximobile.feature.ui.components.StatusPill
import org.example.taximobile.feature.ui.components.StatusTone
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiButtonStyle
import org.example.taximobile.feature.ui.components.TaxiTextField
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*


@Composable
internal fun PlaceDiscoverySection(
    cities: List<PublicRideCity>,
    selectedCityId: String?,
    discovery: PlaceDiscoveryUiState,
    pickupTarget: Boolean,
    pendingAction: AppAction?,
    onSelectCity: (String) -> Unit,
    onSearch: (String, String) -> Unit,
    onSelectResult: (PlaceResult) -> Unit,
) {
    val eligibleCities = cities.filter { it.bookingAvailable }
    val activeCityId = selectedCityId?.takeIf { id -> eligibleCities.any { it.id == id } }
        ?: eligibleCities.firstOrNull()?.id
    // Reopening a picker may restore its last query, but a later response must
    // never replace text the passenger is currently editing.
    var query by remember {
        mutableStateOf(discovery.search?.takeIf { it.cityId == activeCityId }?.query.orEmpty())
    }
    var lastSubmittedKey by remember { mutableStateOf<String?>(null) }
    val normalizedQuery = query.trim().replace(Regex("\\s+"), " ")
    val visibleSearch = discovery.search?.takeIf {
        it.cityId == activeCityId && it.query == normalizedQuery && normalizedQuery.length >= 2
    }
    val requestKey = activeCityId?.let { "$it|$normalizedQuery" }

    fun submitSearch() {
        val cityId = activeCityId ?: return
        if (normalizedQuery.length < 2 || pendingAction != null) return
        lastSubmittedKey = requestKey
        onSearch(cityId, normalizedQuery)
    }

    // Text entry is debounced, while the explicit button provides a predictable
    // retry after an outage or a request rejected by the shared action gate.
    LaunchedEffect(requestKey, pendingAction, visibleSearch?.query) {
        if (
            requestKey == null ||
            normalizedQuery.length < 2 ||
            pendingAction != null ||
            requestKey == lastSubmittedKey ||
            (visibleSearch?.query == normalizedQuery && visibleSearch.cityId == activeCityId)
        ) return@LaunchedEffect
        delay(450)
        lastSubmittedKey = requestKey
        onSearch(requireNotNull(activeCityId), normalizedQuery)
    }

    Text(stringResource(Res.string.place_search_title), style = MaterialTheme.typography.titleMedium)
    Text(
        stringResource(Res.string.place_search_privacy_help),
        style = MaterialTheme.typography.bodySmall,
        color = TaxiColors.Ink500,
    )
    if (eligibleCities.isEmpty()) {
        Text(
            stringResource(Res.string.place_search_no_service_city),
            color = TaxiColors.Ink700,
        )
        Text(
            stringResource(Res.string.place_search_map_fallback),
            style = MaterialTheme.typography.bodySmall,
            color = TaxiColors.Ink500,
        )
        return
    }
    if (eligibleCities.size > 1) {
        Text(stringResource(Res.string.place_search_city), style = MaterialTheme.typography.labelLarge)
        eligibleCities.forEach { city ->
            TaxiButton(
                label = city.name.preferred(androidx.compose.ui.text.intl.Locale.current.language),
                onClick = {
                    lastSubmittedKey = null
                    onSelectCity(city.id)
                },
                style = if (city.id == activeCityId) TaxiButtonStyle.ToneLike else TaxiButtonStyle.Secondary,
                enabled = pendingAction == null,
            )
        }
    }
    TaxiTextField(
        value = query,
        onValueChange = { query = it.take(120) },
        label = stringResource(Res.string.place_search_field),
        modifier = Modifier.testTag("place-search-query"),
        enabled = pendingAction == null,
        imeAction = ImeAction.Search,
    )
    TaxiButton(
        label = stringResource(Res.string.place_search_action),
        onClick = {
            lastSubmittedKey = null
            submitSearch()
        },
        enabled = normalizedQuery.length >= 2 && pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.SEARCH_PLACES, activeCityId),
        style = TaxiButtonStyle.Secondary,
    )
    visibleSearch?.let { search ->
        if (search.items.isEmpty()) {
            Text(
                stringResource(Res.string.place_search_empty),
                color = TaxiColors.Ink700,
            )
        }
        search.items.forEach { result ->
            val canSelect = !pickupTarget || result.pickupServiceable
            TextButton(
                onClick = { onSelectResult(result) },
                enabled = canSelect && pendingAction == null,
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("place-result-${result.id}"),
            ) {
                Column(
                    Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
                ) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(result.primaryText, style = MaterialTheme.typography.bodyLarge)
                        Text(placeKindLabel(result.kind), style = MaterialTheme.typography.labelSmall)
                    }
                    result.secondaryText?.let {
                        Text(it, style = MaterialTheme.typography.bodySmall, color = TaxiColors.Ink500)
                    }
                    if (!result.pickupServiceable) {
                        StatusPill(
                            stringResource(Res.string.place_outside_pickup_area),
                            StatusTone.Warning,
                        )
                    }
                }
            }
        }
        Text(
            stringResource(
                Res.string.place_attribution,
                search.attribution.text,
                search.attribution.url,
            ),
            style = MaterialTheme.typography.labelSmall,
            color = TaxiColors.Ink500,
        )
    }
    Text(
        stringResource(Res.string.place_search_map_fallback),
        style = MaterialTheme.typography.bodySmall,
        color = TaxiColors.Ink500,
    )
}


@Composable
private fun placeKindLabel(kind: PlaceKind): String = stringResource(
    when (kind) {
        PlaceKind.ADDRESS -> Res.string.place_kind_address
        PlaceKind.STREET -> Res.string.place_kind_street
        PlaceKind.LOCALITY -> Res.string.place_kind_locality
        PlaceKind.POI -> Res.string.place_kind_landmark
        PlaceKind.OTHER,
        PlaceKind.UNKNOWN -> Res.string.place_kind_other
    }
)
