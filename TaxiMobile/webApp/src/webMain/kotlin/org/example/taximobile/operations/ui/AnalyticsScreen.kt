package org.example.taximobile.operations.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.OperationalMetricFact
import org.example.taximobile.operations.state.OperationsUiState

@Composable
internal fun AnalyticsScreen(state: OperationsUiState) {
    val analytics = state.snapshot?.analytics
    if (analytics == null) {
        ScreenColumn {
            SectionHeading(
                title = "Rollout intelligence",
                supportingText = "Select an authorized city to load privacy-bounded operational facts.",
            )
            EmptyState(
                "Analytics unavailable",
                "The active grants or city scope do not authorize aggregate operational reporting.",
            )
        }
        return
    }

    val families = remember(analytics.definitions) {
        analytics.definitions.map { it.family }.distinct().sorted()
    }
    var selectedFamily by remember(analytics.facts.toTime) { mutableStateOf<String?>(null) }
    var selectedService by remember(analytics.facts.toTime) { mutableStateOf<String?>(null) }
    val filtered = analytics.facts.items.filter { fact ->
        (selectedFamily == null || fact.metricFamily == selectedFamily) &&
            (selectedService == null || fact.serviceType == selectedService)
    }
    val published = filtered.count { !it.suppressed }
    val suppressed = filtered.size - published
    val latestWatermark = filtered.maxOfOrNull { it.sourceWatermark }

    ScreenColumn {
        SectionHeading(
            title = "Rollout intelligence",
            supportingText = "Hourly, city-scoped aggregates only. These facts inform operations and never authorize rides, money, eligibility, or city activation.",
        )

        Row(
            Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
        ) {
            MetricCard("Published cells", published.toString(), "Cells meeting the privacy threshold", Modifier.width(220.dp))
            MetricCard("Suppressed cells", suppressed.toString(), "All measures hidden below ${analytics.facts.minimumCellSize}", Modifier.width(220.dp))
            MetricCard("Metric definitions", analytics.definitions.size.toString(), analytics.facts.definitionVersion, Modifier.width(220.dp))
            MetricCard("Latest source", compactTimestamp(latestWatermark), "Rebuilt from normalized source records", Modifier.width(230.dp))
        }

        DataCard {
            Column(
                Modifier.fillMaxWidth().padding(TaxiSpacing.Lg),
                verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            ) {
                Text("Reporting contract", color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
                Text(
                    "${analytics.facts.bucket.lowercase().replaceFirstChar { it.uppercase() }} buckets · " +
                        "${analytics.facts.retentionDays}-day retention · " +
                        "late events recomputed from source until retention · no participant-level export",
                    color = TaxiColors.Ink700,
                    style = MaterialTheme.typography.bodyMedium,
                )
                Row(
                    Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                ) {
                    ScopeMenu(
                        label = "Metric family",
                        selected = selectedFamily?.displayLabel() ?: "All families",
                        options = listOf(ScopeOption(null, "All families")) +
                            families.map { ScopeOption(it, it.displayLabel()) },
                        enabled = true,
                        onSelected = { selectedFamily = it },
                    )
                    ScopeMenu(
                        label = "Service",
                        selected = selectedService?.displayLabel() ?: "All services",
                        options = listOf(
                            ScopeOption(null, "All services"),
                            ScopeOption("ON_DEMAND", "On demand"),
                            ScopeOption("FIXED_ROUTE", "Fixed route"),
                        ),
                        enabled = true,
                        onSelected = { selectedService = it },
                    )
                }
            }
        }

        SectionHeading(
            title = "Published aggregate facts",
            supportingText = "Suppressed rows remain visible so missing values cannot be mistaken for zero. Monetary facts are never combined across currencies.",
        )
        if (filtered.isEmpty()) {
            EmptyState("No facts in this view", "Try another metric family, service, or city scope.")
        } else {
            DataCard(tableMinWidth = 1_150.dp) {
                Column(Modifier.fillMaxWidth().widthIn(min = 1_150.dp)) {
                    TableHeader(
                        listOf(
                            "Hour" to 1.0f,
                            "Metric" to 1.8f,
                            "Scope" to 1.25f,
                            "Outcome" to 1.15f,
                            "Published value" to 1.4f,
                            "Samples" to 0.75f,
                            "Source state" to 1.15f,
                        )
                    )
                    filtered.sortedWith(
                        compareByDescending<OperationalMetricFact> { it.bucketStart }
                            .thenBy { it.metricCode }
                    ).forEach { fact ->
                        TableRow {
                            TableCell(compactTimestamp(fact.bucketStart), 1.0f)
                            TableCell(
                                analytics.definitions.firstOrNull { it.code == fact.metricCode }?.title
                                    ?: fact.metricCode.displayLabel(),
                                1.8f,
                                supporting = fact.metricFamily.displayLabel(),
                            )
                            TableCell(
                                fact.serviceType?.displayLabel() ?: "City wide",
                                1.25f,
                                supporting = fact.bookingType?.displayLabel(),
                            )
                            TableCell(
                                fact.outcomeCode?.displayLabel() ?: "—",
                                1.15f,
                                supporting = fact.categoryCode?.displayLabel(),
                            )
                            TableCell(
                                fact.publishedValue(analytics.facts.minimumCellSize),
                                1.4f,
                                supporting = fact.publishedDetail(),
                            )
                            TableCell(fact.sampleCount?.toString() ?: "Hidden", 0.75f)
                            TableCell(
                                if (fact.suppressed) "Privacy suppressed" else "Published",
                                1.15f,
                                supporting = compactTimestamp(fact.sourceWatermark),
                            )
                        }
                    }
                }
            }
        }

        SectionHeading(
            title = "Definitions",
            supportingText = "Each metric has an allowlisted source, purpose, owner, retention period, and stable semantic version.",
        )
        analytics.definitions
            .filter { selectedFamily == null || it.family == selectedFamily }
            .forEach { definition ->
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = TaxiColors.Surface0,
                    shape = RoundedCornerShape(TaxiRadii.Lg),
                    border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
                ) {
                    Column(
                        Modifier.padding(TaxiSpacing.Lg),
                        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
                    ) {
                        Text(definition.title, color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
                        Text(definition.purpose, color = TaxiColors.Ink700, style = MaterialTheme.typography.bodyMedium)
                        Text(
                            "${definition.code} · ${definition.unit} · source: ${definition.source} · owner: ${definition.owner}",
                            color = TaxiColors.Ink500,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }
    }
}

private fun String.displayLabel(): String = lowercase()
    .split('_')
    .joinToString(" ") { word -> word.replaceFirstChar { it.uppercase() } }

private fun OperationalMetricFact.publishedValue(minimumCellSize: Int): String {
    if (suppressed) return "Hidden (<$minimumCellSize)"
    return when {
        amountSum != null -> "$amountSum ${currency.orEmpty()}".trim()
        distributionGini != null -> "Gini $distributionGini"
        averageNumericValue != null -> averageNumericValue
        averageDurationSeconds != null -> "$averageDurationSeconds sec avg"
        averageDistanceMeters != null -> "$averageDistanceMeters m avg"
        integerValue != null -> integerValue.toString()
        else -> "Published"
    }
}

private fun OperationalMetricFact.publishedDetail(): String? {
    if (suppressed) return "Every measure removed"
    if (metricCode == "DRIVER_WORK_DISTRIBUTION") {
        return "avg ${averagePerEntity ?: "—"} · min ${minimumPerEntity ?: "—"} · max ${maximumPerEntity ?: "—"}"
    }
    return matchingAlgorithmVersion?.let { "matching $it" }
        ?: fixedRouteDirectionVersionId?.let { "route ${shortId(it)}" }
}
