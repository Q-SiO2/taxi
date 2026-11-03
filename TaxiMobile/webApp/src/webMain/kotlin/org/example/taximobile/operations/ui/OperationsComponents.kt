package org.example.taximobile.operations.ui

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.state.OperationsMessage
import org.example.taximobile.feature.ui.text.resolve
import org.example.taximobile.feature.ui.text.hasArabicScript
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.example.taximobile.feature.ui.theme.taxiArabicFontFamily
import androidx.compose.ui.text.style.TextDirection
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*
import androidx.compose.foundation.Canvas
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics

@Composable
internal fun OperationsWordmark(compact: Boolean = false) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
    ) {
        Box(
            modifier = Modifier
                .size(38.dp)
                .background(taxiColors.Accent500, RoundedCornerShape(taxiRadii.Md)),
            contentAlignment = Alignment.Center,
        ) {
            Text("TM", color = MaterialTheme.colorScheme.onPrimary, fontWeight = FontWeight.ExtraBold)
        }
        if (!compact) {
            Column {
                Text(
                    "TaxiMobile",
                    color = Color.White,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    stringResource(Res.string.web_operations),
                    color = taxiColors.Navy200,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
    }
}

@Composable
internal fun StatusBadge(status: String, modifier: Modifier = Modifier, label: String? = null) {
    val taxiColors = TaxiTheme.colors
    val normalized = status.uppercase()
    val (background, foreground) = when (normalized) {
        "ACTIVE", "PASSED", "APPROVED", "RESOLVED" -> taxiColors.Success100 to taxiColors.Success600
        "PILOT", "CONFIGURING", "IN_REVIEW", "PENDING", "HIGH", "ACKNOWLEDGED", "IN_PROGRESS" -> taxiColors.Warning100 to taxiColors.Warning600
        "PAUSED", "FAILED", "URGENT", "OPEN", "ESCALATED" -> taxiColors.Danger100 to taxiColors.Danger600
        "RETIRED", "REPLACED", "REVOKED", "CLOSED" -> taxiColors.Surface2 to taxiColors.Ink700
        "DRAFT" -> taxiColors.Navy100 to taxiColors.Navy700
        else -> taxiColors.Info100 to taxiColors.Info600
    }
    Surface(
        modifier = modifier,
        color = background,
        shape = RoundedCornerShape(TaxiTheme.radii.Pill),
        border = BorderStroke(1.dp, foreground.copy(alpha = 0.22f)),
    ) {
        Text(
            label ?: normalized.replace('_', ' '),
            modifier = Modifier.padding(horizontal = TaxiSpacing.Sm, vertical = TaxiSpacing.Xs),
            color = foreground,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
internal fun MessageBanner(
    message: OperationsMessage,
    error: Boolean,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    val background = if (error) taxiColors.Danger100 else taxiColors.Success100
    val foreground = if (error) taxiColors.Danger600 else taxiColors.Success600
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = background,
        shape = RoundedCornerShape(taxiRadii.Md),
        border = BorderStroke(1.dp, foreground.copy(alpha = 0.25f)),
    ) {
        Row(
            modifier = Modifier.padding(TaxiSpacing.Md),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier.size(10.dp).background(foreground, CircleShape),
            )
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xxs)) {
                Text(message.localizedTitle?.resolve() ?: message.title, color = foreground, fontWeight = FontWeight.Bold)
                Text(message.localizedDetail?.resolve() ?: message.detail, color = taxiColors.Ink700, style = MaterialTheme.typography.bodySmall)
            }
            OutlinedButton(
                shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                onClick = onDismiss,
                colors = ButtonDefaults.outlinedButtonColors(contentColor = foreground),
                border = BorderStroke(1.dp, foreground.copy(alpha = 0.45f)),
            ) {
                Text(stringResource(Res.string.web_dismiss))
            }
        }
    }
}

@Composable
internal fun MetricCard(
    label: String,
    value: String,
    supportingText: String,
    modifier: Modifier = Modifier,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Surface(
        modifier = modifier.widthIn(min = 180.dp),
        color = taxiColors.Surface0,
        shape = RoundedCornerShape(taxiRadii.Lg),
        border = BorderStroke(1.dp, taxiColors.StrokeSubtle),
    ) {
        Column(
            Modifier.padding(TaxiSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
        ) {
            Text(label, color = taxiColors.Ink500, style = MaterialTheme.typography.labelMedium)
            Text(value, color = taxiColors.Navy900, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Text(supportingText, color = taxiColors.Ink700, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
internal fun SectionHeading(
    title: String,
    supportingText: String,
    modifier: Modifier = Modifier,
    action: (@Composable () -> Unit)? = null,
) {
    val taxiColors = TaxiTheme.colors
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xxs)) {
            Text(title, style = MaterialTheme.typography.headlineSmall, color = taxiColors.Navy900, fontWeight = FontWeight.Bold)
            Text(supportingText, style = MaterialTheme.typography.bodyMedium, color = taxiColors.Ink500)
        }
        action?.invoke()
    }
}

@Composable
internal fun EmptyState(
    title: String,
    detail: String,
    modifier: Modifier = Modifier,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = taxiColors.Surface0,
        shape = RoundedCornerShape(taxiRadii.Lg),
        border = BorderStroke(1.dp, taxiColors.StrokeSubtle),
    ) {
        Column(
            Modifier.padding(TaxiSpacing.Xxl),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            Box(
                Modifier.size(44.dp).background(taxiColors.Navy100, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Text("—", color = taxiColors.Navy700, fontWeight = FontWeight.Bold)
            }
            Text(title, color = taxiColors.Navy900, style = MaterialTheme.typography.titleMedium)
            Text(detail, color = taxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
        }
    }
}

data class ScopeOption(val id: String?, val label: String)

@Composable
internal fun ScopeMenu(
    label: String,
    selected: String,
    options: List<ScopeOption>,
    enabled: Boolean,
    onSelected: (String?) -> Unit,
    modifier: Modifier = Modifier,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    var expanded by remember { mutableStateOf(false) }
    Box(modifier) {
        Surface(
            modifier = Modifier
                .widthIn(min = 150.dp, max = 230.dp)
                .semantics { contentDescription = "$label: $selected" }
                .clickable(enabled = enabled, role = Role.Button) { expanded = true },
            color = taxiColors.Surface0,
            shape = RoundedCornerShape(taxiRadii.Md),
            border = BorderStroke(1.dp, taxiColors.StrokeSubtle),
        ) {
            Column(Modifier.padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Xs)) {
                Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = taxiColors.Ink500)
                Row(verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    Text(selected, Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium,
                        color = taxiColors.Navy900, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Canvas(Modifier.size(18.dp)) {
                        val middle = Offset(size.width * 0.5f, size.height * 0.65f)
                        drawLine(taxiColors.Navy900, Offset(size.width * 0.25f, size.height * 0.4f), middle, 1.8.dp.toPx())
                        drawLine(taxiColors.Navy900, middle, Offset(size.width * 0.75f, size.height * 0.4f), 1.8.dp.toPx())
                    }
                }
            }
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(option.label, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                    onClick = {
                        expanded = false
                        onSelected(option.id)
                    },
                )
            }
        }
    }
}

@Composable
internal fun DataCard(
    modifier: Modifier = Modifier,
    tableMinWidth: Dp? = null,
    content: @Composable () -> Unit,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    if (tableMinWidth != null) {
        BoxWithConstraints(modifier.fillMaxWidth()) {
            val cardWidth = if (maxWidth < tableMinWidth) tableMinWidth else maxWidth
            Box(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
                Surface(
                    modifier = Modifier.width(cardWidth),
                    color = taxiColors.Surface0,
                    shape = RoundedCornerShape(taxiRadii.Lg),
                    border = BorderStroke(1.dp, taxiColors.StrokeSubtle),
                    content = content,
                )
            }
        }
    } else {
        Surface(
            modifier = modifier.fillMaxWidth(),
            color = taxiColors.Surface0,
            shape = RoundedCornerShape(taxiRadii.Lg),
            border = BorderStroke(1.dp, taxiColors.StrokeSubtle),
            content = content,
        )
    }
}

@Composable
internal fun KeyValue(label: String, value: String, modifier: Modifier = Modifier) {
    val taxiColors = TaxiTheme.colors
    Column(modifier, verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xxs)) {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall, color = taxiColors.Ink500)
        Text(value, style = MaterialTheme.typography.bodyMedium.copy(textDirection = TextDirection.Content),
            fontFamily = if (hasArabicScript(value)) taxiArabicFontFamily() else null, color = taxiColors.Ink900)
    }
}

@Composable
internal fun PageLimitNote(shown: Int, total: Int) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    if (total <= shown) return
    Spacer(Modifier.height(TaxiSpacing.Sm))
    Text(
        stringResource(Res.string.web_page_limit_note, ltrIsolate(shown.toString()), ltrIsolate(total.toString())),
        color = taxiColors.Warning600,
        style = MaterialTheme.typography.bodySmall,
        modifier = Modifier
            .fillMaxWidth()
            .background(taxiColors.Warning100, RoundedCornerShape(taxiRadii.Sm))
            .border(1.dp, taxiColors.Warning600.copy(alpha = 0.2f), RoundedCornerShape(taxiRadii.Sm))
            .padding(TaxiSpacing.Sm),
    )
}

internal fun shortId(value: String?): String = when {
    value == null -> "—"
    value.length <= 12 -> value
    else -> "${value.take(8)}…${value.takeLast(4)}"
}

internal fun compactTimestamp(value: String?): String {
    if (value == null) return "—"
    val withoutZulu = value.removeSuffix("Z")
    val positiveOffset = withoutZulu.indexOf('+', startIndex = 10)
    val negativeOffset = withoutZulu.indexOf('-', startIndex = 11)
    val offsetIndex = listOf(positiveOffset, negativeOffset)
        .filter { it >= 0 }
        .minOrNull()
    val dateTime = if (offsetIndex == null) withoutZulu else withoutZulu.substring(0, offsetIndex)
    val core = dateTime.substringBefore('.').replace('T', ' ')
    val isUtc = value.endsWith('Z') || value.contains("+00:00")
    val offset = offsetIndex?.let { withoutZulu.substring(it) }
    return when {
        isUtc -> "$core UTC"
        offset != null -> "$core $offset"
        else -> core
    }
}
