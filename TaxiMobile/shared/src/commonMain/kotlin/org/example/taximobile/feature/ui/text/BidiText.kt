package org.example.taximobile.feature.ui.text

/**
 * Isolate a machine identifier from surrounding RTL prose without changing the
 * identifier itself. LRI/PDI are invisible Unicode bidi controls and remain
 * safe when the same presentation is rendered in an LTR locale.
 */
fun ltrIsolate(value: String): String = "\u2066$value\u2069"

/** Choose a font with Arabic glyphs for mixed user content in any UI language. */
fun hasArabicScript(value: String): Boolean = value.any { character ->
    character.code in 0x0600..0x06ff || character.code in 0x0750..0x077f ||
        character.code in 0x08a0..0x08ff || character.code in 0xfb50..0xfdff ||
        character.code in 0xfe70..0xfeff
}
