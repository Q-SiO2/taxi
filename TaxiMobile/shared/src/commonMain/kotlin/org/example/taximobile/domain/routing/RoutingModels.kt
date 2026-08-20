package org.example.taximobile.domain.routing

import org.example.taximobile.domain.rides.Coordinates

data class RouteManeuver(
    val instruction: String,
    val distanceMeters: Int,
    val durationSeconds: Int,
    val beginShapeIndex: Int,
    val endShapeIndex: Int,
)

data class RoutePlan(
    val distanceMeters: Int,
    val durationSeconds: Int,
    val geometry: List<Coordinates>,
    val maneuvers: List<RouteManeuver>,
)

interface RoutingGateway {
    suspend fun route(origin: Coordinates, destination: Coordinates): RoutePlan
}
