"""Real MFA/scope/replay/rollback and concurrent staff member-register commands."""

import asyncio
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from test_operator_membership_authority import closed_shop, database
from test_dispatch_candidate_contention import seed_ride
from test_mvp_lifecycle import require_integration_settings
from test_scheduled_live_protection import assert_no_live_acceptance
from test_operations_mfa_flow import (
    TOTP_SECRET, age_session_mfa, begin_login, integration_settings,
    seed_operations_factor, totp_code,
)
from workload_fixtures import seed_workload_supply
from taximobile_api.domains.administration.models import AdministrativeGrant, AdministrativeRoleTemplate, AuditLog
from taximobile_api.domains.cooperatives import operations_router as commands
from taximobile_api.domains.cooperatives.models import Cooperative, CooperativeMembership
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.idempotency.models import IdempotencyRecord
from taximobile_api.domains.markets.constants import LEGACY_MARKET_ID, LEGACY_OPERATOR_ID
from taximobile_api.domains.markets.models import Market, Operator, OperatorType
from taximobile_api.domains.matching.service import dispatch_ride
from taximobile_api.domains.rides.models import Ride, RideStatus
from taximobile_api.domains.rides.service import accept_offer_atomically, RideOfferUnavailable
from taximobile_api.main import create_app

pytestmark = pytest.mark.integration


def prepare():
    settings = integration_settings()
    actor_id = asyncio.run(seed_operations_factor(settings))
    async def seed(sessions):
        await seed_workload_supply(sessions, 3)
        async with sessions.begin() as session:
            await closed_shop(session)
            drivers = list(await session.scalars(select(DriverProfile.id).order_by(DriverProfile.id)))
            other_register = Cooperative(name="Synthetic separate register")
            session.add(other_register)
            await session.flush()
            other_operator = Operator(market_id=LEGACY_MARKET_ID, cooperative_id=other_register.id,
                operator_type=OperatorType.COOPERATIVE, name="Synthetic no-assignment operator")
            session.add(other_operator)
            await session.flush()
            return drivers, other_operator.id
    drivers, other = database(seed)
    return settings, actor_id, drivers, other


def headers(client):
    challenge = begin_login(client)
    verification = client.post("/api/v1/operations/auth/mfa/verify", json={
        "challenge_id": challenge["challenge_id"],
        "code": totp_code(TOTP_SECRET, int(datetime.now(UTC).timestamp() // 30)),
    })
    assert verification.status_code == 200, verification.text
    return {"Authorization": f"Bearer {verification.json()['access_token']}", "Idempotency-Key": uuid4().hex}


def enrollment(driver_id, number="SYNTHETIC-001"):
    return {"driver_id": str(driver_id), "status": "ACTIVE", "membership_number": number,
            "joined_at": (datetime.now(UTC)-timedelta(days=1)).isoformat(), "ended_at": None,
            "reason": "Verified synthetic roster reference"}


def test_operator_register_scope_without_fixed_route_assignment():
    """Inspecting an on-demand operator must not fail the whole web snapshot."""
    settings, _, _, _ = prepare()
    city = "10000000-0000-4000-8000-000000000003"
    with TestClient(create_app(settings=settings), base_url="https://testserver", raise_server_exceptions=False) as client:
        auth = headers(client)
        for suffix in ("fixed-routes", "fixed-route-fare-options"):
            path = f"/api/v1/operations/cities/{city}/{suffix}?operator_id={LEGACY_OPERATOR_ID}"
            assert client.get(path).status_code == 401
            result = client.get(path, headers=auth)
            assert result.status_code == 200, result.text
            assert result.json()['items'] == []
        draft = client.post(f"/api/v1/operations/cities/{city}/fixed-routes", headers=auth,
                            json={"operator_id": str(LEGACY_OPERATOR_ID), "code": "NO_ASSIGNMENT"})
        assert draft.status_code == 409, draft.text
        assert "active fixed-route assignment" in draft.text


def edit(member, **changes):
    return {"status": "SUSPENDED", "membership_number": member['membership_number'],
            "joined_at": member['joined_at'], "ended_at": member['ended_at'],
            "expected_updated_at": member['updated_at'], "reason": "Synthetic register review", **changes}


@pytest.mark.parametrize("scenario", ["lifecycle", "scope-replay", "stale-mfa", "rollback", "foreign-driver", "pagination"])
def test_operator_member_register_http(scenario, monkeypatch):
    settings, actor_id, drivers, other_operator = prepare()
    url = f"/api/v1/operations/operators/{LEGACY_OPERATOR_ID}/memberships"
    with TestClient(create_app(settings=settings), base_url="https://testserver", raise_server_exceptions=False) as client:
        auth = headers(client)
        payload = enrollment(drivers[0])
        assert client.get(url).status_code == 401
        assert client.post(url, json=payload).status_code == 401
        if scenario == "stale-mfa":
            current = client.get('/api/v1/operations/auth/session', headers=auth).json()
            asyncio.run(age_session_mfa(settings, UUID(current['session_id'])))
            assert client.get(url, headers=auth).status_code == 200
            assert client.post(url, headers=auth, json=payload).status_code == 403
            return
        if scenario == "foreign-driver":
            foreign = f"/api/v1/operations/operators/{other_operator}/memberships"
            assert client.get(foreign, headers=auth).json()['total'] == 0
            assert client.post(foreign, headers=auth, json=payload).status_code == 404
            assert client.post(url, headers=auth, json=payload | {'driver_id':str(uuid4())}).status_code == 404
        if scenario == "rollback":
            original = commands.audit
            async def failed_audit(*args, **kwargs):
                await original(*args, **kwargs)
                raise RuntimeError("private synthetic audit failure")
            with monkeypatch.context() as patch:
                patch.setattr(commands, 'audit', failed_audit)
                failed = client.post(url, headers=auth, json=payload)
            assert failed.status_code == 500 and 'private synthetic' not in failed.text
            assert client.get(url, headers=auth).json()['total'] == 0
        created = client.post(url, headers=auth, json=payload)
        assert created.status_code == 201, created.text
        member = created.json()
        assert 'email' not in member and 'user_id' not in member and member['driver_id'] == str(drivers[0])
        replay = client.post(url, headers=auth, json=payload)
        assert replay.status_code == 201 and replay.json() == member
        assert client.post(url, headers=auth, json=payload | {'reason':'A different reason'}).status_code == 409
        assert client.post(url, headers=auth | {'Idempotency-Key':uuid4().hex}, json=payload).status_code == 409
        if scenario == "pagination":
            for i, driver in enumerate(drivers[1:]):
                result=client.post(url, headers=auth | {'Idempotency-Key':uuid4().hex}, json=enrollment(driver, f'SYNTHETIC-{i+2}'))
                assert result.status_code == 201, result.text
            for page in (1,2,3):
                result=client.get(url, headers=auth, params={'page':page,'limit':1})
                assert result.status_code==200 and result.json()['total']==3 and len(result.json()['items'])==1
            assert client.get(f'/api/v1/operations/operators/{other_operator}/memberships', headers=auth).json()['total']==0
        elif scenario == "scope-replay":
            async def restrict(sessions):
                async with sessions.begin() as session:
                    market=Market(code='ZZ', name='Synthetic unrelated market', default_currency='MAD')
                    session.add(market); await session.flush()
                    grant=await session.scalar(select(AdministrativeGrant).where(AdministrativeGrant.user_id==actor_id))
                    grant.market_id=market.id
            database(restrict)
            assert client.get(url, headers=auth).status_code == 404
            assert client.post(url, headers=auth, json=payload).status_code == 404
            assert client.patch(url+'/'+member['id'], headers=auth, json=edit(member)).status_code == 404
        else:
            change = edit(member, membership_number=None, ended_at=datetime.now(UTC).isoformat())
            patch_auth=auth | {'Idempotency-Key':uuid4().hex}
            if scenario == "rollback":
                with monkeypatch.context() as patch:
                    patch.setattr(commands,'audit',failed_audit)
                    assert client.patch(url+'/'+member['id'],headers=patch_auth,json=change).status_code==500
                assert client.get(url,headers=auth).json()['items'][0]['status']=='ACTIVE'
            changed=client.patch(url+'/'+member['id'],headers=patch_auth,json=change)
            assert changed.status_code==200, changed.text
            assert changed.json()['status']=='SUSPENDED' and changed.json()['membership_number'] is None
            assert client.patch(url+'/'+member['id'],headers=patch_auth,json=change).json()==changed.json()
            assert client.patch(url+'/'+member['id'],headers=auth | {'Idempotency-Key':uuid4().hex},json=change).status_code==409
            assert client.patch(f'/api/v1/operations/operators/{other_operator}/memberships/{member["id"]}',headers=patch_auth,json=change).status_code==404
    async def durable(sessions):
        async with sessions() as session:
            logs=list(await session.scalars(select(AuditLog).where(AuditLog.resource_type=='cooperative_membership')))
            assert logs and all('membership_number' not in log.changes.get('current', {}) for log in logs)
            assert all('membership_number' not in log.changes.get('previous', {}) for log in logs)
            assert all('SYNTHETIC-' not in str(log.changes) for log in logs)
            assert len(logs)==(3 if scenario=='pagination' else 1 if scenario=='scope-replay' else 2)
            assert await session.scalar(select(func.count(CooperativeMembership.id)))==(3 if scenario=='pagination' else 1)
            assert await session.scalar(select(func.count(IdempotencyRecord.id)).where(IdempotencyRecord.operation.like('op-member-%')))==len(logs)
    database(durable)


@pytest.mark.parametrize('same_key', [True,False])
def test_concurrent_staff_edits_cannot_duplicate_or_overwrite_a_decision(same_key):
    settings, _, drivers, _ = prepare()
    url=f'/api/v1/operations/operators/{LEGACY_OPERATOR_ID}/memberships'
    with TestClient(create_app(settings=settings),base_url='https://testserver') as client:
        auth=headers(client)
        member=client.post(url,headers=auth,json=enrollment(drivers[0])).json()
        payload=edit(member)
        first=auth | {'Idempotency-Key':uuid4().hex}
        second=first if same_key else auth | {'Idempotency-Key':uuid4().hex}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(client.patch,url+'/'+member['id'],headers=h,json=payload) for h in (first,second)]
            results=[f.result(timeout=30) for f in futures]
        assert sorted(r.status_code for r in results)==([200,200] if same_key else [200,409])
        if same_key: assert results[0].json()==results[1].json()
    async def durable(sessions):
        async with sessions() as session:
            assert await session.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='OPERATOR_MEMBERSHIP_UPDATED'))==1
    database(durable)


@pytest.mark.parametrize('scenario',['operator-admin','unlinked','number-collision'])
def test_register_maintenance_does_not_expand_roles_or_bypass_register_constraints(scenario):
    settings, actor_id, drivers, _ = prepare()
    url=f'/api/v1/operations/operators/{LEGACY_OPERATOR_ID}/memberships'
    if scenario in ('operator-admin','unlinked'):
        async def change(sessions):
            async with sessions.begin() as session:
                if scenario=='operator-admin':
                    grant=await session.scalar(select(AdministrativeGrant).where(AdministrativeGrant.user_id==actor_id))
                    grant.market_id=None; grant.operator_id=LEGACY_OPERATOR_ID
                    grant.role_template=AdministrativeRoleTemplate.OPERATOR_ADMIN
                else:
                    operator=await session.get(Operator,LEGACY_OPERATOR_ID)
                    operator.requires_active_membership=False
                    operator.cooperative_id=None; operator.operator_type=OperatorType.LOCAL_ENTITY
        database(change)
    with TestClient(create_app(settings=settings),base_url='https://testserver') as client:
        auth=headers(client)
        if scenario=='number-collision':
            first=client.post(url,headers=auth,json=enrollment(drivers[0]))
            assert first.status_code==201, first.text
            second=client.post(url,headers=auth | {'Idempotency-Key':uuid4().hex},json=enrollment(drivers[1]))
            assert second.status_code==409, second.text
            assert client.get(url,headers=auth).json()['total']==1
        else:
            expected=403 if scenario=='operator-admin' else 409
            assert client.get(url,headers=auth).status_code==expected
            assert client.post(url,headers=auth,json=enrollment(drivers[0])).status_code==expected
    async def durable(sessions):
        async with sessions() as session:
            expected=1 if scenario=='number-collision' else 0
            assert await session.scalar(select(func.count(CooperativeMembership.id)))==expected
            assert await session.scalar(select(func.count(AuditLog.id)).where(AuditLog.resource_type=='cooperative_membership'))==expected
    database(durable)


def test_actual_staff_decisions_control_new_assignment_and_preserve_an_accepted_trip():
    settings, _, drivers, _=prepare()
    url=f'/api/v1/operations/operators/{LEGACY_OPERATOR_ID}/memberships'
    with TestClient(create_app(settings=settings),base_url='https://testserver') as client:
        auth=headers(client)
        member=client.post(url,headers=auth,json=enrollment(drivers[0])).json()
        async def offer(sessions):
            ride_id=await seed_ride(sessions)
            async with sessions.begin() as session:
                offered=await dispatch_ride(session,ride_id,replace(require_integration_settings(),ride_offer_seconds=300))
                assert offered is not None and offered.driver_id==drivers[0]
                return ride_id, offered.id
        ride_id, offer_id=database(offer)
        suspended=client.patch(url+'/'+member['id'],headers=auth | {'Idempotency-Key':uuid4().hex},json=edit(member))
        assert suspended.status_code==200,suspended.text
        async def rejected(sessions):
            async with sessions.begin() as session:
                with pytest.raises(RideOfferUnavailable,match='membership'):
                    await accept_offer_atomically(session,offer_id,drivers[0])
            async with sessions() as session:
                await assert_no_live_acceptance(session,ride_id,offer_id)
        database(rejected)
        reinstated=client.patch(url+'/'+member['id'],headers=auth | {'Idempotency-Key':uuid4().hex},json=edit(suspended.json(),status='ACTIVE'))
        assert reinstated.status_code==200,reinstated.text
        async def accept(sessions):
            async with sessions.begin() as session:
                await accept_offer_atomically(session,offer_id,drivers[0])
        database(accept)
        ended=client.patch(url+'/'+member['id'],headers=auth | {'Idempotency-Key':uuid4().hex},json=edit(reinstated.json(),status='ENDED'))
        assert ended.status_code==200,ended.text
    async def preserved(sessions):
        async with sessions() as session:
            ride=await session.get(Ride,ride_id)
            assert ride.status==RideStatus.ACCEPTED and ride.driver_id==drivers[0]
    database(preserved)
