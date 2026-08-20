package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.layout.size
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.disabled
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.loading

@Composable
fun MapFab(
    label: String,
    glyph: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    loading: Boolean = false,
) {
    val loadingDescription = stringResource(Res.string.loading)
    FloatingActionButton(
        onClick = { if (enabled && !loading) onClick() },
        modifier = modifier.size(52.dp).semantics {
            contentDescription = label
            if (!enabled || loading) disabled()
            if (loading) stateDescription = loadingDescription
        },
        containerColor = TaxiColors.Surface0,
        contentColor = TaxiColors.Navy900,
    ) {
        if (loading) {
            CircularProgressIndicator(
                color = TaxiColors.Navy900,
                strokeWidth = 2.dp,
                modifier = Modifier.size(20.dp),
            )
        } else {
            Text(glyph)
        }
    }
}
