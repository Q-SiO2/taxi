"""Actual migrated/PostGIS HTTP recovery. Inert synthetic CI fixtures only."""
import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from secrets import token_urlsafe
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.domains.auth.models import User, UserRole, Role
from taximobile_api.domains.auth.security import hash_password
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.markets.constants import LEGACY_CITY_ID, LEGACY_OPERATOR_ID
from taximobile_api.domains.payments.models import Payment, PaymentMethod, PaymentStatus, DriverEarning
from taximobile_api.domains.rides.models import Ride, RideStatus
from taximobile_api.main import create_app
from test_mvp_lifecycle import require_integration_settings
from workload_fixtures import seed_workload_supply

pytestmark = pytest.mark.integration
QUEUE = "/api/v1/drivers/me/payments/cash/pending"


def test_pending_cash_recovers_old_work_is_private_paginated_and_removed_once_settled():
    settings = replace(require_integration_settings(), process_role="api")

    async def seed():
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            drivers = await seed_workload_supply(sessions, 2, loginable=True)
            password = token_urlsafe(24)
            expected = []
            async with sessions.begin() as session:
                passenger = User(email=f"queue-{uuid4().hex}@example.test", password_hash=hash_password(password))
                session.add(passenger)
                await session.flush()
                session.add(UserRole(user_id=passenger.id, role=Role.PASSENGER))
                profiles = [await session.scalar(select(DriverProfile).where(DriverProfile.user_id == UUID(d['user_id']))) for d in drivers]
                now = datetime.now(UTC)
                scenarios = [(PaymentMethod.CASH, PaymentStatus.PENDING, RideStatus.COMPLETED, 0) for _ in range(23)]
                scenarios += [(PaymentMethod.CASH, s, RideStatus.COMPLETED, 0) for s in PaymentStatus if s != PaymentStatus.PENDING]
                scenarios += [(PaymentMethod.MANUAL_TRANSFER, PaymentStatus.PENDING, RideStatus.COMPLETED, 0),
                              (PaymentMethod.CASH, PaymentStatus.PENDING, RideStatus.COMPLETED, 1),
                              (PaymentMethod.CASH, PaymentStatus.PENDING, RideStatus.IN_PROGRESS, 0)]
                for index, (method, state, ride_state, owner) in enumerate(scenarios):
                    recorded = now - timedelta(days=30) + timedelta(seconds=index)
                    ride = Ride(city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
                                passenger_id=passenger.id, driver_id=profiles[owner].id,
                                pickup_point=WKTElement('POINT(-7.5898 33.5731)', srid=4326),
                                destination_point=WKTElement('POINT(-7.6039 33.5899)', srid=4326),
                                status=ride_state, payment_method=method, created_at=recorded,
                                completed_at=recorded if ride_state == RideStatus.COMPLETED else None)
                    session.add(ride)
                    await session.flush()
                    payment = Payment(ride_id=ride.id, payer_id=passenger.id,
                                      city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
                                      method=method, status=state, amount=Decimal('35.00'), currency='MAD', created_at=recorded)
                    session.add(payment)
                    await session.flush()
                    if owner == 0 and method == PaymentMethod.CASH and state == PaymentStatus.PENDING and ride_state == RideStatus.COMPLETED:
                        expected.append(str(ride.id))
                # Recent history is full of newer completed/settled rides. The
                # pending queue must not depend on which history page is loaded.
                for index in range(25):
                    ride = Ride(city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
                                passenger_id=passenger.id, driver_id=profiles[0].id,
                                pickup_point=WKTElement('POINT(-7.5898 33.5731)', srid=4326),
                                destination_point=WKTElement('POINT(-7.6039 33.5899)', srid=4326),
                                status=RideStatus.COMPLETED, completed_at=now, created_at=now + timedelta(seconds=index))
                    session.add(ride)
                    await session.flush()
                    session.add(Payment(ride_id=ride.id, payer_id=passenger.id,
                                        city_id=LEGACY_CITY_ID, operator_id=LEGACY_OPERATOR_ID,
                                        method=PaymentMethod.CASH, status=PaymentStatus.COMPLETED, amount=Decimal('35.00'), currency='MAD'))
            return drivers, {'identifier': passenger.email, 'password': password}, expected
        finally:
            await engine.dispose()

    drivers, passenger, expected = asyncio.run(seed())
    def login(client, person):
        r = client.post('/api/v1/auth/login', json={'identifier': person['identifier'], 'password': person['password']})
        assert r.status_code == 200, 'Synthetic login failed'
        return {'Authorization': 'Bearer ' + r.json()['access_token']}

    with TestClient(create_app(settings=settings)) as client:
        driver = login(client, drivers[0])
        other = login(client, drivers[1])
        passenger_headers = login(client, passenger)
        assert client.get(QUEUE).status_code == 401
        assert client.get(QUEUE, headers=passenger_headers).status_code == 404
        first = client.get(QUEUE, headers=driver)
        assert first.status_code == 200
        data = first.json()
        assert data['total'] == 23 and data['page'] == 1 and data['limit'] == 20
        assert [x['ride_id'] for x in data['items']] == expected[:20]
        assert all(set(x) == {'payment_id','ride_id','amount','currency','created_at','completed_at','method','status'} for x in data['items'])
        assert all(x['method'] == 'CASH' and x['status'] == 'PENDING' and x['amount'] == '35.00' for x in data['items'])
        second = client.get(QUEUE, headers=driver, params={'page': 2}).json()
        assert [x['ride_id'] for x in second['items']] == expected[20:]
        history = client.get('/api/v1/drivers/me/rides', headers=driver).json()
        assert all(x['id'] not in expected for x in history['items'])
        other_data = client.get(QUEUE, headers=other).json()
        assert other_data['total'] == 1 and other_data['items'][0]['ride_id'] not in expected
        for params in [{'page': 0}, {'limit': 101}, {'limit': 0}, {'page': -1}]:
            assert client.get(QUEUE, headers=driver, params=params).status_code == 422
        assert client.get(QUEUE, headers=driver, params={'page': 99}).json()['items'] == []
        target = expected[0]
        url = f'/api/v1/rides/{target}/payments/cash/settle'
        for forbidden in (other, passenger_headers):
            assert client.post(url, headers={**forbidden,'Idempotency-Key':str(uuid4())}).status_code in (403,404)
        before = client.get('/api/v1/drivers/me/earnings', headers=driver).json()
        command = {**driver, 'Idempotency-Key': str(uuid4())}
        settled = client.post(url, headers=command)
        assert settled.status_code == 200 and settled.json()['status'] == 'COMPLETED'
        assert client.post(url, headers=command).json() == settled.json()
        after = client.get('/api/v1/drivers/me/earnings', headers=driver).json()
        assert after['count'] == before['count'] + 1
        assert Decimal(after['net']) == Decimal(before['net']) + Decimal('35.00')
        remaining = client.get(QUEUE, headers=driver).json()
        assert remaining['total'] == 22 and target not in [x['ride_id'] for x in remaining['items']]
        # A fresh login/read has no client completion-screen memory.
        recovered = login(client, drivers[0])
        assert client.get(QUEUE, headers=recovered).json() == remaining
