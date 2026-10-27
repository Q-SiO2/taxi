"""Real authenticated city visibility and non-mutating clock resolution."""

import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.domains.idempotency.models import IdempotencyRecord
from taximobile_api.domains.markets.constants import LEGACY_MARKET_ID
from taximobile_api.domains.markets.models import City, CityLifecycleStatus
from taximobile_api.domains.outbox.models import OutboxEvent
from taximobile_api.domains.scheduled_bookings.models import (
    ScheduledBooking, ScheduledBookingOffer, ScheduledBookingCommitment, ScheduledBookingEvent,
)
from taximobile_api.main import create_app
from test_mvp_lifecycle import require_integration_settings, register_and_login, authorization

pytestmark = pytest.mark.integration


def test_authenticated_clock_planning_respects_city_visibility_and_writes_no_business_records():
    settings = require_integration_settings()
    ids = [uuid4() for _ in range(3)]
    states = [CityLifecycleStatus.ACTIVE, CityLifecycleStatus.PAUSED, CityLifecycleStatus.DRAFT]

    async def database(action):
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessions.begin() as session:
                if action == 'seed':
                    session.add_all([City(id=id_, market_id=LEGACY_MARKET_ID, code=f'clock-{id_.hex}',
                        localized_name={'en': 'Synthetic clock city'}, timezone='Africa/Casablanca',
                        presentation_centroid=WKTElement('POINT(-5 34)', srid=4326), lifecycle_status=state)
                        for id_, state in zip(ids, states)])
                elif action == 'cleanup':
                    await session.execute(delete(City).where(City.id.in_(ids)))
                else:
                    return {model.__tablename__: await session.scalar(select(func.count()).select_from(model))
                            for model in [ScheduledBooking, ScheduledBookingOffer, ScheduledBookingCommitment,
                                          ScheduledBookingEvent, IdempotencyRecord, OutboxEvent]}
        finally:
            await engine.dispose()

    asyncio.run(database('seed'))
    try:
        with TestClient(create_app(settings=settings)) as client:
            token = register_and_login(client, email=f'clock-{uuid4().hex}@example.test',
                password='Synthetic-clock-test-2026', display_name='Synthetic clock passenger')
            headers = authorization(token)
            before = asyncio.run(database('snapshot'))
            endpoint = f'/api/v1/cities/{ids[0]}/scheduled-time-options'
            clock = {'local_date': '2026-02-15', 'local_time': '02:30'}
            assert client.post(endpoint, json=clock).status_code == 401
            assert client.post(endpoint, json=clock, headers=authorization('invalid-synthetic')).status_code == 401
            response = client.post(endpoint, json=clock, headers=headers)
            assert response.status_code == 200, response.text
            result = response.json()
            assert set(result) == {'city_id', 'city_timezone', 'local_date', 'local_time', 'booking_available', 'rules_version', 'options'}
            assert response.headers['cache-control'] == 'no-store'
            assert [x['utc_offset_seconds'] for x in result['options']] == [3600, 0]
            assert all(set(x) == {'scheduled_for', 'utc_offset_seconds'} for x in result['options'])
            # Active but unconfigured cannot acquire booking authority through this read.
            assert result['booking_available'] is False
            gap = client.post(endpoint, headers=headers, json={'local_date': '2026-03-22', 'local_time': '02:30'})
            assert gap.status_code == 200 and gap.json()['options'] == []
            normal = client.post(endpoint, headers=headers, json={'local_date': '2026-11-01', 'local_time': '09:30'})
            assert normal.status_code == 200 and len(normal.json()['options']) == 1
            paused = client.post(f'/api/v1/cities/{ids[1]}/scheduled-time-options', json=clock, headers=headers)
            assert paused.status_code == 200 and paused.json()['booking_available'] is False
            for hidden in [ids[2], uuid4()]:
                assert client.post(f'/api/v1/cities/{hidden}/scheduled-time-options', json=clock, headers=headers).status_code == 404
            assert client.post(endpoint, json=clock | {'local_time': '24:00'}, headers=headers).status_code == 422
            assert client.post(endpoint, json=clock | {'timezone': 'UTC'}, headers=headers).status_code == 422
            assert asyncio.run(database('snapshot')) == before
    finally:
        asyncio.run(database('cleanup'))
