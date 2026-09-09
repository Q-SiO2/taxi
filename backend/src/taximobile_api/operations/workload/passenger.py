"""Real API commands with bounded concurrency, recovery and no SQL shortcuts.

The caller must confirm exclusive synthetic use of the target and its providers.
An origin or confirmation flag cannot prove that a deployment has no real users.
Accounts and history intentionally remain for audit in the disposable environment.
"""

import asyncio
from secrets import token_urlsafe
from time import perf_counter
from uuid import uuid4

import httpx

from .config import PassengerWorkloadConfig
from .metrics import WorkloadMetrics
from .client import StepFailure, WorkloadClient


class PassengerClient(WorkloadClient):
    async def provision(self, index: int) -> None:
        email = f"load-{self.metrics.run_id}-{index}@taximobile.invalid"
        password = token_urlsafe(32)
        registered = await self.request("register", "POST", "/api/v1/auth/register", 201, payload={
            "email": email, "password": password, "display_name": "Synthetic Workload Passenger",
        })
        self.metrics.provisioned += 1
        self.check(isinstance(registered.get("user"), dict), "register")
        user_id = self.resource_id(registered["user"], "register")
        auth = await self.request("login", "POST", "/api/v1/auth/login", 200, payload={
            "identifier": email, "password": password, "device_label": "synthetic-workload",
        })
        token = auth.get("access_token")
        self.check(isinstance(token, str) and 1 <= len(token) <= 8192 and token.isascii()
                   and not any(c.isspace() for c in token), "login")
        self.token = token
        me = await self.request("identity", "GET", "/api/v1/me", 200)
        self.check(me.get("roles") == ["PASSENGER"] and me.get("id") == user_id, "identity")

    async def journey(self) -> None:
        self.metrics.started += 1
        started = perf_counter()
        create_key, cancel_key = str(uuid4()), str(uuid4())
        payload = {**self.config.ride_payload(), "payment_method": "CASH"}
        ride_id = None
        create_attempted = False
        try:
            quote = await self.request("estimate", "POST", "/api/v1/rides/estimate", 200,
                                       payload=self.config.ride_payload())
            self.check(isinstance(quote.get("payment_methods"), list)
                       and "CASH" in quote["payment_methods"]
                       and isinstance(quote.get("estimate"), dict)
                       and quote["estimate"].get("city_id") == str(self.config.city_id), "estimate")
            create_attempted = True
            self.metrics.unresolved_commands.add(create_key)
            created = await self.request("create", "POST", "/api/v1/rides", 201,
                                         payload=payload, key=create_key)
            ride_id = self.resource_id(created, "create")
            replay = await self.request("create_replay", "POST", "/api/v1/rides", 201,
                                        payload=payload, key=create_key)
            self.check(replay == created, "create_replay")
            restored = await self.request("restore", "GET", f"/api/v1/rides/{ride_id}", 200)
            self.check(restored.get("id") == ride_id
                       and restored.get("city_id") == str(self.config.city_id)
                       and restored.get("payment_method") == "CASH"
                       and restored.get("status") in ("REQUESTED", "MATCHING")
                       and restored.get("driver") is None, "restore")
            cancelled = await self.cancel(ride_id, cancel_key, "cancel")
            replay = await self.cancel(ride_id, cancel_key, "cancel_replay")
            self.check(replay == cancelled, "cancel_replay")
            await self.verify_cancelled(ride_id, create_key, "terminal_restore")
            self.metrics.completed += 1
        except StepFailure:
            # Resolve an ambiguous create at most once, using the ORIGINAL key.
            # A successful recovery never erases the original failed measurement.
            if create_attempted:
                try:
                    if ride_id is None:
                        recovered = await self.request("recover_create", "POST", "/api/v1/rides", 201,
                                                       payload=payload, key=create_key)
                        ride_id = self.resource_id(recovered, "recover_create")
                    await self.cancel(ride_id, cancel_key, "recover_cancel")
                    await self.verify_cancelled(ride_id, create_key, "recover_restore")
                except StepFailure:
                    pass  # Already counted; unresolved command remains in report.
            raise
        finally:
            self.metrics.journey_latencies.append((perf_counter() - started) * 1000)

    async def cancel(self, ride_id: str, key: str, step: str) -> dict:
        result = await self.request(step, "POST", f"/api/v1/rides/{ride_id}/cancel", 200,
                                    payload={"reason": "Synthetic workload cancellation"}, key=key)
        self.check(result.get("id") == ride_id and result.get("status") == "CANCELLED", step)
        return result

    async def verify_cancelled(self, ride_id: str, create_key: str, step: str) -> None:
        result = await self.request(step, "GET", f"/api/v1/rides/{ride_id}", 200)
        self.check(result.get("id") == ride_id and result.get("status") == "CANCELLED", step)
        self.metrics.unresolved_commands.discard(create_key)


async def run_passenger_workload(config: PassengerWorkloadConfig, *, transport=None) -> dict:
    metrics = WorkloadMetrics(run_id=uuid4().hex)
    stopped = asyncio.Event()
    started = perf_counter()
    async with httpx.AsyncClient(
        base_url=config.base_url.rstrip("/"), timeout=config.request_timeout_seconds,
        limits=httpx.Limits(max_connections=config.users, max_keepalive_connections=config.users),
        follow_redirects=False, trust_env=False, transport=transport,
    ) as http:
        actors = [PassengerClient(http, config, metrics) for _ in range(config.users)]

        async def worker(actor: PassengerClient) -> None:
            for index in range(config.journeys_per_user):
                if stopped.is_set() or metrics.failures:
                    return
                try:
                    await actor.journey()
                except StepFailure:
                    stopped.set()
                    return
                if index + 1 < config.journeys_per_user:
                    await asyncio.sleep(config.interval_seconds)

        try:
            async with asyncio.timeout(config.duration_seconds):
                # Admission uses the real registration/login limits, not a SQL seed
                # or elevated credentials. No ride writes until all accounts work.
                for index, actor in enumerate(actors):
                    await actor.provision(index)
                async with asyncio.TaskGroup() as group:
                    for actor in actors:
                        group.create_task(worker(actor))
        except StepFailure:
            stopped.set()
        except TimeoutError:
            metrics.deadline_exceeded = True
    report = metrics.report(
        elapsed=perf_counter() - started,
        planned=config.users * config.journeys_per_user,
        p95_budget_ms=config.p95_budget_ms,
    )
    report["load_shape"] = {
        "model": "CLOSED_LOOP",
        "users": config.users,
        "journeys_per_user": config.journeys_per_user,
        "interval_seconds": config.interval_seconds,
        "request_timeout_seconds": config.request_timeout_seconds,
        "duration_limit_seconds": config.duration_seconds,
        "admission_included_in_elapsed": True,
    }
    return report
