package org.example.taximobile.data.network

import kotlin.random.Random

/** Collision-resistant command identifier; it is not an authentication secret. */
fun newIdempotencyKey(): String = buildString {
    repeat(2) {
        append(Random.nextLong().toULong().toString(16).padStart(16, '0'))
    }
}
