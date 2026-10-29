package org.example.taximobile.operations.data

import kotlinx.coroutines.CancellationException
import org.example.taximobile.operations.model.OperationsTokens
import kotlin.coroutines.Continuation
import kotlin.coroutines.EmptyCoroutineContext
import kotlin.coroutines.startCoroutine
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertSame
import kotlin.test.assertTrue

class OperationsAccessRefreshTest {
    private val old = OperationsTokens("expired-access", "one-use-refresh", "csrf-old", 600, "MFA")
    private val replacement = OperationsTokens("fresh-access", null, "csrf-new", 600, "MFA")

    @Test
    fun `expired logout rotates once and revokes the replacement session`() {
        val events = mutableListOf<String>()
        val revoked = immediate {
            withOperationsAccessRefresh(old, { refresh, csrf ->
                assertEquals(old.refreshToken, refresh)
                assertEquals(old.csrfToken, csrf)
                events += "refresh"
                replacement
            }, { events += "publish:${it.accessToken}" }) { access ->
                events += "logout:$access"
                if (access == old.accessToken) throw OperationsApiException(401, "Expired")
                "revoked"
            }
        }
        assertEquals("revoked", revoked)
        assertEquals(listOf("logout:expired-access", "refresh", "publish:fresh-access", "logout:fresh-access"), events)
    }

    @Test
    fun `successful logout does not rotate a refresh credential`() {
        var requests = 0
        immediate { withOperationsAccessRefresh(old, { _, _ -> error("Unexpected refresh") }, { error("Unexpected publication") }) {
            assertEquals(old.accessToken, it)
            requests++
        } }
        assertEquals(1, requests)
    }

    @Test
    fun `unknown result permission denial and cancellation never replay logout`() {
        for (failure in listOf(RuntimeException("Unknown transport result"), OperationsApiException(403, "Denied"), CancellationException("Stopped"))) {
            var requests = 0
            val actual = assertFailsWith<Throwable> {
                immediate { withOperationsAccessRefresh(old, { _, _ -> error("Unexpected refresh") }, { error("Unexpected publication") }) {
                    requests++
                    throw failure
                } }
            }
            assertSame(failure, actual)
            assertEquals(1, requests)
        }
    }

    @Test
    fun `unknown refresh result is not retried or published`() {
        var rotations = 0
        var requests = 0
        val unknown = RuntimeException("Refresh response lost")
        val actual = assertFailsWith<RuntimeException> {
            immediate { withOperationsAccessRefresh(old, { _, _ -> rotations++; throw unknown }, { error("Unconfirmed rotation") }) {
                requests++
                throw OperationsApiException(401, "Expired")
            } }
        }
        assertSame(unknown, actual)
        assertEquals(1, rotations)
        assertEquals(1, requests)
    }

    @Test
    fun `second rejection keeps the published rotation and cannot loop`() {
        var rotations = 0
        var published: OperationsTokens? = null
        var requests = 0
        val actual = assertFailsWith<OperationsApiException> {
            immediate { withOperationsAccessRefresh(old, { _, _ -> rotations++; replacement }, { published = it }) {
                requests++
                throw OperationsApiException(401, "Revoked")
            } }
        }
        assertEquals(401, actual.statusCode)
        assertEquals(replacement, published)
        assertEquals(1, rotations)
        assertEquals(2, requests)
    }
}

/** These callbacks complete synchronously; no clock or scheduler simulation. */
private fun <T> immediate(block: suspend () -> T): T {
    var completed = false
    var outcome: Result<T>? = null
    block.startCoroutine(object : Continuation<T> {
        override val context = EmptyCoroutineContext
        override fun resumeWith(result: Result<T>) { outcome = result; completed = true }
    })
    assertTrue(completed, "Expected a synchronous fake transport")
    return requireNotNull(outcome).getOrThrow()
}
