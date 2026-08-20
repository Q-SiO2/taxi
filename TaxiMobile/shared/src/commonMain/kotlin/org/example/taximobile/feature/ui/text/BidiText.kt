package org.example.taximobile.feature.ui.text

/**
 * Isolate a machine identifier from surrounding RTL prose without changing the
 * identifier itself. LRI/PDI are invisible Unicode bidi controls and remain
 * safe when the same presentation is rendered in an LTR locale.
 */
fun ltrIsolate(value: String): String = "\u2066$value\u2069"
