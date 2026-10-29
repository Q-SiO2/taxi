package org.example.taximobile.core.time

/** Keep browser timezone initialization reachable only when named-zone formatting is used. */
internal expect fun cityTimeZoneSupportAvailable(): Boolean
