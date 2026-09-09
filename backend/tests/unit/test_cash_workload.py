import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from taximobile_api.operations.cash_workload import main, run_cash_workload
from taximobile_api.operations.workload.drivers import SyntheticDriverCredential, parse_driver_credentials, DriverClient, claim_driver
from taximobile_api.operations.workload.metrics import WorkloadMetrics
from taximobile_api.operations.workload.passenger import PassengerClient
from test_passenger_workload import SyntheticAPI, configuration


ECONOMICS = {
    "transport_fare": "35.00", "scheduling_surcharge": "0.00", "operator_service_fee": "0.00",
    "passenger_total": "35.00", "expected_driver_net": "35.00", "operator_allocation": "0.00",
    "operator_fee_policy_version": "synthetic-v1", "operator_fee_calculation_mode": "FLAT_PER_COMPLETED_BOOKING",
    "operator_fee_funding_mode": "DRIVER_SETTLEMENT_DEDUCTION", "scheduling_policy_version": None,
}


class CashAPI(SyntheticAPI):
    def __init__(self, config):
        super().__init__(config)
        self.credentials = tuple(SyntheticDriverCredential(uuid4(), f"driver-secret-{uuid4().hex}") for _ in range(config.users))
        self.drivers = {f"Bearer {credential.access_token}": {"user_id": str(credential.user_id), "status": "OFFLINE",
                                                            "offer": None, "earnings": []} for credential in self.credentials}
        self.payments = {}
        self.driver_commands = {}
        self.foreign_offer_id = str(uuid4())

    async def __call__(self, request):
        await asyncio.sleep(0)
        path = request.url.path
        owner = request.headers.get("Authorization")
        driver = self.drivers.get(owner)
        if driver is not None:
            self.calls.append((request.method, path, dict(request.headers), None))
            if path == "/api/v1/me":
                return httpx.Response(200, json={"id": driver["user_id"], "roles": ["DRIVER"]})
            if path == "/api/v1/drivers/me":
                return httpx.Response(200, json={"user_id": driver["user_id"], "display_name": "Synthetic driver",
                    "account_status": "ACTIVE", "verification_status": "APPROVED", "availability_status": driver["status"]})
            if path.endswith("/location"):
                assert json.loads(request.content)["latitude"] == self.config.pickup[0]
                return httpx.Response(200, json={"accepted": True})
            if "/availability" in path:
                if path.endswith("/online"):
                    assert driver["status"] == "OFFLINE"
                    driver["status"] = "AVAILABLE"
                if path.endswith("/offline"):
                    assert driver["status"] == "AVAILABLE"
                    driver["status"] = "OFFLINE"
                return httpx.Response(200, json={"status": driver["status"], "city_id": str(self.config.city_id), "service_type": "ON_DEMAND"})
            if path.endswith("/ride-offers"):
                offers = [] if driver["offer"] is None else [
                    {"id": self.foreign_offer_id, "ride_id": str(uuid4())}, driver["offer"],
                ]
                return httpx.Response(200, json={"offers": offers})
            if path.endswith("/accept"):
                assert path.split("/")[4] != self.foreign_offer_id
                ride_id = driver["offer"]["ride_id"]
                assert path.split("/")[4] == driver["offer"]["id"]
                ride = self.rides[ride_id][1]
                ride["status"], ride["driver"] = "ACCEPTED", {"display_name": "Synthetic driver"}
                driver["status"] = "EN_ROUTE"
                driver["ride"] = ride_id
                driver["offer"] = None
                return httpx.Response(200, json={"ride_id": ride_id, "status": "ACCEPTED"})
            if path.endswith("/earnings"):
                return httpx.Response(200, json={"items": driver["earnings"]})
            ride_id = path.split("/")[4]
            assert driver["ride"] == ride_id
            ride = self.rides[ride_id][1]
            key = request.headers.get("Idempotency-Key")
            if key in self.driver_commands:
                return httpx.Response(200, json=self.driver_commands[key])
            status = {"en-route": "DRIVER_EN_ROUTE", "arrived": "DRIVER_ARRIVED", "start": "IN_PROGRESS", "complete": "COMPLETED"}.get(path.rsplit("/", 1)[1])
            if status:
                ride["status"] = status
                result = {"ride_id": ride_id, "status": status}
                if status == "IN_PROGRESS":
                    driver["status"] = "ON_RIDE"
                if status == "COMPLETED":
                    result.update({"payment_method": "CASH", "fare": {"amount": "35.00", "currency": "MAD"}})
                    self.payments[ride_id] = {"id": str(uuid4()), "ride_id": ride_id, "amount": "35.00", "currency": "MAD", "method": "CASH", "status": "PENDING"}
                    driver["status"] = "OFFLINE"
            else:
                assert path.endswith("/payments/cash/settle")
                self.payments[ride_id]["status"] = "COMPLETED"
                result = dict(self.payments[ride_id])
                driver["earnings"].append({"ride_id": ride_id, "gross": "35.00", "fees": "0.00", "adjustments": "0.00", "net": "35.00", "operator_allocation": "0.00", "currency": "MAD"})
            if key:
                self.driver_commands[key] = result
            return httpx.Response(200, json=result)
        if path.endswith("/receipt"):
            ride_id = path.split("/")[4]
            assert self.rides[ride_id][0] == owner
            return httpx.Response(200, json={"ride_id": ride_id, "payment": dict(self.payments[ride_id]),
                "fare": {"amount": "35.00", "currency": "MAD", "economics": {k: v for k, v in ECONOMICS.items() if v is not None}}})
        response = await super().__call__(request)
        body = response.json()
        if path.endswith("/estimate"):
            body["estimate"].update({"amount": "35.00", "currency": "MAD", "economics": ECONOMICS})
        if path == "/api/v1/rides" and not any(d.get("ride") == body["id"] or (d["offer"] and d["offer"]["ride_id"] == body["id"]) for d in self.drivers.values()):
            selected = next(d for d in self.drivers.values() if d["status"] == "AVAILABLE")
            selected["status"] = "OFFERED_RIDE"
            selected["offer"] = {"ride_id": body["id"], "id": str(uuid4())}
        return httpx.Response(response.status_code, json=body)


def run(config, api, handler=None):
    return asyncio.run(run_cash_workload(config, api.credentials, confirm_synthetic_cash=True,
                                        transport=httpx.MockTransport(handler or api)))


def test_two_roles_complete_two_waves_with_exact_replay_and_no_credential_output():
    config = configuration()
    api = CashAPI(config)
    report = run(config, api)
    assert report["passed"] and report["completed_journeys"] == 4
    assert report["drivers_not_confirmed_offline"] == report["unresolved_ride_commands"] == 0
    assert len(api.payments) == 4 and sum(len(d["earnings"]) for d in api.drivers.values()) == 4
    assert all(d["status"] == "OFFLINE" for d in api.drivers.values())
    for credential in api.credentials:
        assert credential.access_token not in json.dumps(report)
        assert credential.access_token not in repr(credential)
        assert str(credential.user_id) not in json.dumps(report)


@pytest.mark.parametrize("raw", ["", "null", "{}", "[1]", '[{"access_token":"secret"}]',
    json.dumps([{"user_id": str(uuid4()), "access_token": "bad\nsecret"}]),
    json.dumps([{"user_id": str(uuid4()), "access_token": 1}]),
    json.dumps([{"user_id": "not-id", "access_token": "secret"}])])
def test_credential_input_fails_closed_without_echoing(raw):
    with pytest.raises(ValueError, match="bounded list") as caught:
        parse_driver_credentials(raw, count=1)
    assert "secret" not in str(caught.value)


def test_duplicate_driver_identity_or_token_refused():
    first = {"user_id": str(uuid4()), "access_token": "secret"}
    for second in (first, {**first, "user_id": str(uuid4())}, {**first, "access_token": "another"}):
        with pytest.raises(ValueError):
            parse_driver_credentials(json.dumps([first, second]), count=2)


@pytest.mark.parametrize("defect", ["identity", "role", "name", "busy"])
def test_driver_preflight_failure_causes_no_writes(defect):
    config = configuration(users=1)
    api = CashAPI(config)
    async def handler(request):
        response = await api(request)
        body = response.json()
        if request.url.path == "/api/v1/me":
            if defect == "identity": body["id"] = str(uuid4())
            if defect == "role": body["roles"] = ["DRIVER", "ADMIN"]
        if request.url.path == "/api/v1/drivers/me":
            if defect == "name": body["display_name"] = "Real driver"
            if defect == "busy": body["availability_status"] = "ON_RIDE"
        return httpx.Response(response.status_code, json=body)
    report = run(config, api, handler)
    assert not report["passed"] and not api.accounts and not api.rides
    assert all(method == "GET" for method, _, _, _ in api.calls)


@pytest.mark.parametrize("defect", ["wrong_total", "pending_paid", "duplicate_earning", "wrong_net", "changed_replay"])
def test_money_or_replay_mismatch_is_failure_not_fake_settlement_success(defect):
    config = configuration(users=1, journeys_per_user=1)
    api = CashAPI(config)
    completions = 0
    async def handler(request):
        nonlocal completions
        response = await api(request)
        body = response.json()
        path = request.url.path
        if path.endswith("/complete"):
            completions += 1
            if defect == "wrong_total": body["fare"]["amount"] = "34.00"
            if defect == "changed_replay" and completions == 2: body["status"] = "IN_PROGRESS"
        if path.endswith("/payments/cash/settle") and defect == "pending_paid": body["status"] = "PENDING"
        if path.endswith("/earnings"):
            if defect == "duplicate_earning": body["items"].append(body["items"][0])
            if defect == "wrong_net": body["items"][0]["net"] = "34.00"
        return httpx.Response(response.status_code, json=body)
    report = run(config, api, handler)
    assert not report["passed"] and report["unresolved_ride_commands"] == 1
    assert report["completed_journeys"] == 0
    assert not any(path.endswith("/cancel") for _, path, _, _ in api.calls)


def test_lost_start_response_never_cancels_or_completes_an_uncertain_active_ride():
    config = configuration(users=1, journeys_per_user=2)
    api = CashAPI(config)
    async def handler(request):
        result = await api(request)
        if request.url.path.endswith("/start"):
            raise httpx.ReadTimeout("private start detail", request=request)
        return result
    report = run(config, api, handler)
    assert not report["passed"] and report["started_journeys"] == 1
    assert report["drivers_not_confirmed_offline"] == 1
    assert report["unresolved_ride_commands"] == 1
    assert not api.payments
    assert not any(path.endswith("/cancel") or path.endswith("/complete") for _, path, _, _ in api.calls)
    assert "private start detail" not in json.dumps(report)


def test_cli_requires_explicit_simulated_cash_confirmation(capsys):
    assert main(["--city-id", str(uuid4()), "--pickup", "0", "0", "--destination", "1", "1"]) == 2
    assert "Confirm simulated cash" in capsys.readouterr().err


def test_partial_online_setup_failure_returns_available_drivers_offline():
    config = configuration()
    api = CashAPI(config)
    online = 0
    async def handler(request):
        nonlocal online
        if request.url.path.endswith("/online"):
            online += 1
            if online == 2:
                return httpx.Response(409)
        return await api(request)
    report = run(config, api, handler)
    assert not report["passed"] and report["started_journeys"] == 0
    assert report["drivers_not_confirmed_offline"] == 0
    assert all(driver["status"] == "OFFLINE" for driver in api.drivers.values())


def test_opposite_driver_offers_do_not_livelock_polling_passengers():
    async def scenario():
        config = configuration()
        metrics = WorkloadMetrics("synthetic")
        barrier = asyncio.Event()
        calls = 0
        ride_a, ride_b = str(uuid4()), str(uuid4())
        drivers = [DriverClient(None, config, metrics, SyntheticDriverCredential(uuid4(), "synthetic")) for _ in range(2)]
        for driver, ride in zip(drivers, (ride_b, ride_a)):
            async def offers(*args, target=ride, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    barrier.set()
                if calls <= 2:
                    await barrier.wait()
                return {"offers": [{"id": str(uuid4()), "ride_id": target}]}
            driver.request = offers
        async def passenger(ride):
            actor = PassengerClient(None, config, metrics)
            async with claim_driver(actor, drivers, ride) as (driver, _):
                return driver
        result = await asyncio.wait_for(asyncio.gather(passenger(ride_a), passenger(ride_b)), .5)
        assert result == [drivers[1], drivers[0]]
        assert not any(driver.busy.locked() for driver in drivers)
    asyncio.run(scenario())
