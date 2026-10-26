@file:OptIn(kotlin.js.ExperimentalWasmJsInterop::class)

package org.example.taximobile.core.time

@JsModule("@js-joda/timezone")
private external object CityTimeZoneModule : JsAny

private fun moduleAvailable(module: JsAny?): Boolean = js("module != null")

// Reachable through the shared formatter, without an unconditional module root.
internal actual fun cityTimeZoneSupportAvailable(): Boolean = moduleAvailable(CityTimeZoneModule)
