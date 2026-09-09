"""Paired synthetic cash journey and exact cross-surface financial checks."""

from decimal import Decimal
import re
from time import perf_counter
from uuid import uuid4

from .client import StepFailure
from .drivers import claim_driver
from .passenger import PassengerClient


class CashPassengerClient(PassengerClient):
    def amount(self, value, step):
        self.check(isinstance(value, str) and len(value) <= 32
                   and re.fullmatch(r"-?[0-9]+(?:\.[0-9]{1,2})?", value) is not None, step)
        return Decimal(value)

    async def restored(self, ride_id, status):
        body = await self.request("cash_restore", "GET", f"/api/v1/rides/{ride_id}", 200)
        self.check(body.get("id") == ride_id and body.get("status") == status
                   and body.get("city_id") == str(self.config.city_id)
                   and body.get("payment_method") == "CASH", "cash_restore")
        return body

    async def replay_command(self, driver, step, path, payload=None):
        key = str(uuid4())
        first = await driver.request(step, "POST", path, 200, payload=payload, key=key)
        second = await driver.request(f"{step}_replay", "POST", path, 200, payload=payload, key=key)
        self.check(first == second, f"{step}_replay")
        return first

    async def cash_journey(self, drivers):
        self.metrics.started += 1
        started = perf_counter()
        create_key = str(uuid4())
        ride_id = None
        start_attempted = False
        try:
            quote = await self.request("cash_estimate", "POST", "/api/v1/rides/estimate", 200,
                                       payload=self.config.ride_payload())
            self.check(isinstance(quote.get("estimate"), dict)
                       and isinstance(quote.get("payment_methods"), list)
                       and "CASH" in quote["payment_methods"], "cash_estimate")
            estimate = quote["estimate"]
            self.check(estimate.get("city_id") == str(self.config.city_id)
                       and isinstance(estimate.get("economics"), dict), "cash_estimate")
            total = self.amount(estimate.get("amount"), "cash_estimate")
            self.check(total >= 0 and self.amount(estimate["economics"].get("passenger_total"), "cash_estimate") == total,
                       "cash_estimate")
            payload = {**self.config.ride_payload(), "payment_method": "CASH"}
            self.metrics.unresolved_commands.add(create_key)
            created = await self.request("cash_create", "POST", "/api/v1/rides", 201, payload=payload, key=create_key)
            ride_id = self.resource_id(created, "cash_create")
            replay = await self.request("cash_create_replay", "POST", "/api/v1/rides", 201, payload=payload, key=create_key)
            self.check(created == replay, "cash_create_replay")
            restored = await self.restored(ride_id, "MATCHING")
            self.check(restored.get("driver") is None, "cash_restore")
            async with claim_driver(self, drivers, ride_id) as (driver, offer_id):
                accepted = await driver.request("driver_accept", "POST", f"/api/v1/ride-offers/{offer_id}/accept", 200)
                self.check(accepted.get("ride_id") == ride_id and accepted.get("status") == "ACCEPTED", "driver_accept")
                restored = await self.restored(ride_id, "ACCEPTED")
                self.check(isinstance(restored.get("driver"), dict), "cash_restore")
                for command, status in (("en-route", "DRIVER_EN_ROUTE"), ("arrived", "DRIVER_ARRIVED"), ("start", "IN_PROGRESS")):
                    if command == "start":
                        start_attempted = True  # A lost response cannot authorize cancellation.
                    transition = await driver.request(f"driver_{command}", "POST", f"/api/v1/rides/{ride_id}/{command}", 200)
                    self.check(transition.get("ride_id") == ride_id and transition.get("status") == status, f"driver_{command}")
                    await self.restored(ride_id, status)
                completed = await self.replay_command(driver, "driver_complete", f"/api/v1/rides/{ride_id}/complete",
                    {"latitude": self.config.destination[0], "longitude": self.config.destination[1]})
                self.check(completed.get("ride_id") == ride_id and completed.get("status") == "COMPLETED"
                           and completed.get("payment_method") == "CASH"
                           and isinstance(completed.get("fare"), dict), "driver_complete")
                self.check(self.amount(completed["fare"].get("amount"), "driver_complete") == total
                           and completed["fare"].get("currency") == estimate.get("currency"), "driver_complete")
                await self.restored(ride_id, "COMPLETED")
                pending = await self.request("cash_pending_receipt", "GET", f"/api/v1/rides/{ride_id}/receipt", 200)
                self.check(isinstance(pending.get("payment"), dict)
                           and pending["payment"].get("status") == "PENDING", "cash_pending_receipt")
                paid = await self.replay_command(driver, "driver_settle_cash", f"/api/v1/rides/{ride_id}/payments/cash/settle")
                self.check(paid.get("ride_id") == ride_id and paid.get("method") == "CASH"
                           and paid.get("status") == "COMPLETED"
                           and paid.get("currency") == estimate.get("currency")
                           and self.amount(paid.get("amount"), "driver_settle_cash") == total, "driver_settle_cash")
                receipt = await self.request("cash_paid_receipt", "GET", f"/api/v1/rides/{ride_id}/receipt", 200)
                self.check(receipt.get("ride_id") == ride_id and isinstance(receipt.get("payment"), dict)
                           and receipt["payment"].get("method") == "CASH"
                           and receipt["payment"].get("status") == "COMPLETED"
                           and isinstance(receipt.get("fare"), dict), "cash_paid_receipt_identity")
                fare = receipt["fare"]
                self.check(self.amount(fare.get("amount"), "cash_paid_receipt") == total
                           and fare.get("currency") == estimate.get("currency"), "cash_paid_receipt_amount")
                self.check(isinstance(fare.get("economics"), dict), "cash_paid_receipt_economics")
                # Receipt serialization excludes nulls; estimates include them.
                # Only the optional scheduling version permits absent/null parity.
                self.check(set(fare["economics"]) - {"scheduling_policy_version"}
                           == set(estimate["economics"]) - {"scheduling_policy_version"}, "cash_receipt_field_set")
                for field in ("transport_fare", "scheduling_surcharge", "operator_service_fee", "passenger_total",
                              "expected_driver_net", "operator_allocation", "operator_fee_policy_version",
                              "operator_fee_calculation_mode", "operator_fee_funding_mode", "scheduling_policy_version"):
                    self.check(fare["economics"].get(field) == estimate["economics"].get(field),
                               f"cash_receipt_{field}")
                earnings = await driver.request("driver_earnings", "GET", "/api/v1/drivers/me/earnings?limit=100", 200)
                self.check(isinstance(earnings.get("items"), list), "driver_earnings")
                entries = [item for item in earnings["items"] if isinstance(item, dict) and item.get("ride_id") == ride_id]
                self.check(len(entries) == 1, "driver_earnings")
                earning = entries[0]
                net = self.amount(earning.get("net"), "driver_earnings")
                allocation = self.amount(earning.get("operator_allocation"), "driver_earnings")
                self.check(earning.get("currency") == estimate.get("currency")
                           and net == self.amount(estimate["economics"].get("expected_driver_net"), "driver_earnings")
                           and allocation == self.amount(estimate["economics"].get("operator_allocation"), "driver_earnings")
                           and net + allocation == total
                           and self.amount(earning.get("gross"), "driver_earnings")
                           - self.amount(earning.get("fees"), "driver_earnings")
                           + self.amount(earning.get("adjustments"), "driver_earnings") == net, "driver_earnings")
                self.metrics.unresolved_commands.discard(create_key)
                self.metrics.completed += 1
        except StepFailure:
            # No synthesized trip completion, settlement, refund, or deletion as
            # "cleanup". Only a known pre-start ride can be safely cancelled.
            if ride_id is not None and not start_attempted:
                try:
                    await self.cancel(ride_id, str(uuid4()), "cash_recover_cancel")
                    await self.verify_cancelled(ride_id, create_key, "cash_recover_restore")
                except StepFailure:
                    pass
            raise
        finally:
            self.metrics.journey_latencies.append((perf_counter() - started) * 1000)
