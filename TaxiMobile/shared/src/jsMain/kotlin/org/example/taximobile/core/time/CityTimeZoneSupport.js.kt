package org.example.taximobile.core.time

@JsModule("@js-joda/timezone")
@JsNonModule
private external object CityTimeZoneModule

// Referencing the module registers named zones before the formatter reads them.
// An exported root would retain the full database in unrelated web entry points.
internal actual fun cityTimeZoneSupportAvailable(): Boolean =
    jsTypeOf(CityTimeZoneModule) != "undefined"
