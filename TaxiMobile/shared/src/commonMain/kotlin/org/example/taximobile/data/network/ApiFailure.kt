package org.example.taximobile.data.network

/** A non-auth backend error safe to display after product-specific translation. */
class ApiRequestException(
    val statusCode: Int,
    message: String,
) : Exception(message)
