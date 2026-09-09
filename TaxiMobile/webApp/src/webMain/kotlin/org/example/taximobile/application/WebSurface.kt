package org.example.taximobile.application

enum class WebSurface { OPERATIONS, APPLICANT }

/** Keeps public applicant and protected operations composition roots separate. */
fun selectWebSurface(pathname: String, hash: String): WebSurface {
    val normalizedPath = "/${pathname.trim().trim('/').lowercase()}"
    val normalizedHash = hash.trim().lowercase().removePrefix("#")
    return if (
        normalizedPath == "/apply" || normalizedPath.startsWith("/apply/") ||
        normalizedHash == "/apply" || normalizedHash.startsWith("/apply?")
    ) {
        WebSurface.APPLICANT
    } else {
        WebSurface.OPERATIONS
    }
}
