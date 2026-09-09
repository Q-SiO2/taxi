package org.example.taximobile.operations.data

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class OperationsApiEndpointsTest {
    @Test
    fun buildsOneVersionedApiPrefix() {
        val endpoints = OperationsApiEndpoints("https://taxi.example/api/v1/")

        assertEquals(
            "https://taxi.example/api/v1/operations/cities",
            endpoints.url("operations/cities"),
        )
    }

    @Test
    fun rejectsMissingOrDuplicatedVersionPrefix() {
        val missing = assertFailsWith<IllegalArgumentException> {
            OperationsApiEndpoints("https://taxi.example")
        }
        val duplicated = assertFailsWith<IllegalArgumentException> {
            OperationsApiEndpoints("https://taxi.example/api/v1/api/v1")
        }

        assertTrue(missing.message.orEmpty().contains("end with /api/v1"))
        assertTrue(duplicated.message.orEmpty().contains("prefix twice"))
    }

    @Test
    fun rejectsRoutesThatCanEscapeTheReviewedPathContract() {
        val endpoints = OperationsApiEndpoints("http://127.0.0.1:8000/api/v1")

        assertFailsWith<IllegalArgumentException> { endpoints.url("/operations/cities") }
        assertFailsWith<IllegalArgumentException> { endpoints.url("operations//cities") }
        assertFailsWith<IllegalArgumentException> { endpoints.url("operations/cities?page=2") }
        assertFailsWith<IllegalArgumentException> { endpoints.url("operations/cities#selection") }
    }
}
