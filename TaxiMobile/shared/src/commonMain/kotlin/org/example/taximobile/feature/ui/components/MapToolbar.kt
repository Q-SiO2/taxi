package org.example.taximobile.feature.ui.components

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing

/** The same quiet map chrome serves both roles; icon shapes never carry the accessible label. */
@Composable
fun MapToolbar(
    accountLabel: String,
    displayName: String?,
    safetyLabel: String,
    inboxLabel: String,
    unreadCount: Int,
    onAccount: () -> Unit,
    onSafety: () -> Unit,
    onInbox: () -> Unit,
    modifier: Modifier = Modifier,
    accountDisplayLabel: String = accountLabel,
) {
    val taxiColors = TaxiTheme.colors
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        MapToolbarAction(accountLabel, onAccount, Modifier.weight(1f).semantics {
            displayName?.ifBlank { null }?.let { stateDescription = it }
        }, icon = MapToolbarIcon.Account) {
            Text(
                accountDisplayLabel,
                style = MaterialTheme.typography.labelLarge,
                color = taxiColors.Navy900,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        MapToolbarAction(safetyLabel, onSafety, icon = MapToolbarIcon.Safety)
        MapToolbarAction(inboxLabel, onInbox, icon = MapToolbarIcon.Inbox) {
            if (unreadCount > 0) {
                Surface(shape = CircleShape, color = taxiColors.Accent500) {
                    Text(
                        unreadCount.coerceAtMost(9).toString() + if (unreadCount > 9) "+" else "",
                        modifier = Modifier.padding(horizontal = 5.dp, vertical = 1.dp),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onPrimary,
                    )
                }
            }
        }
    }
}

private enum class MapToolbarIcon { Account, Safety, Inbox }

@Composable
private fun MapToolbarAction(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    icon: MapToolbarIcon,
    trailing: @Composable () -> Unit = {},
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Surface(
        modifier = modifier.semantics { contentDescription = label; role = Role.Button }.clickable(onClick = onClick),
        shape = RoundedCornerShape(taxiRadii.Pill),
        color = taxiColors.Surface0,
        shadowElevation = if (TaxiTheme.style == org.example.taximobile.feature.ui.theme.TaxiStyle.Notepad) 0.dp else 3.dp,
    ) {
        Row(
            modifier = Modifier.defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)
                .padding(horizontal = TaxiSpacing.Sm),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            MapToolbarGlyph(icon)
            trailing()
        }
    }
}

@Composable
private fun MapToolbarGlyph(icon: MapToolbarIcon) {
    val taxiColors = TaxiTheme.colors
    Canvas(Modifier.size(24.dp)) {
        val unit = size.width / 24f
        val stroke = 1.9f * unit
        fun point(x: Float, y: Float) = Offset(x * unit, y * unit)
        when (icon) {
            MapToolbarIcon.Account -> {
                drawCircle(taxiColors.Navy900, radius = 3.2f * unit, center = point(12f, 8f), style = Stroke(stroke))
                drawArc(taxiColors.Navy900, startAngle = 200f, sweepAngle = 140f, useCenter = false,
                    topLeft = point(4.5f, 13f), size = androidx.compose.ui.geometry.Size(15f * unit, 11f * unit),
                    style = Stroke(stroke))
            }
            MapToolbarIcon.Safety -> {
                val shield = Path().apply {
                    moveTo(12f * unit, 2.5f * unit)
                    lineTo(19f * unit, 5.3f * unit)
                    lineTo(18f * unit, 14f * unit)
                    lineTo(12f * unit, 21f * unit)
                    lineTo(6f * unit, 14f * unit)
                    lineTo(5f * unit, 5.3f * unit)
                    close()
                }
                drawPath(shield, taxiColors.Navy900, style = Stroke(stroke))
                drawLine(taxiColors.Navy900, point(9f, 11.8f), point(11.2f, 14f), stroke)
                drawLine(taxiColors.Navy900, point(11.2f, 14f), point(15.6f, 9.5f), stroke)
            }
            MapToolbarIcon.Inbox -> {
                val tray = Path().apply {
                    moveTo(4f * unit, 7f * unit)
                    lineTo(20f * unit, 7f * unit)
                    lineTo(21f * unit, 18f * unit)
                    lineTo(3f * unit, 18f * unit)
                    close()
                }
                drawPath(tray, taxiColors.Navy900, style = Stroke(stroke))
                drawLine(taxiColors.Navy900, point(4f, 13f), point(9f, 13f), stroke)
                drawLine(taxiColors.Navy900, point(9f, 13f), point(11f, 15f), stroke)
                drawLine(taxiColors.Navy900, point(11f, 15f), point(13f, 15f), stroke)
                drawLine(taxiColors.Navy900, point(13f, 15f), point(15f, 13f), stroke)
                drawLine(taxiColors.Navy900, point(15f, 13f), point(20f, 13f), stroke)
            }
        }
    }
}
