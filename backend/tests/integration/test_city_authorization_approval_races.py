"""One city cannot acquire duplicate authority through approval/reinstatement."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from assignment_concurrency import contended_commands
from scheduled_handoff_fixtures import prepare_handoff_fixture
from test_city_driver_recruitment import seed_recruiting_test_city
from test_city_authorization_lifecycle import command, authorization_for
from test_mvp_lifecycle import require_integration_settings
from taximobile_api.domains.driver_applications.authorization_lifecycle import AuthorizationDecisionRequest, decide_authorization
from taximobile_api.domains.driver_applications.models import (
    DriverApplicationEvidence, DriverCityApplication, DriverCityAuthorization,
    DriverCityAuthorizationService, DriverRequirementItem, DriverRequirementVersion,
)
from taximobile_api.domains.driver_applications.schemas import ApplicationDecisionRequest
from taximobile_api.domains.driver_applications.service import RecruitmentConflict, decide_application, select_active_authorization
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.markets.models import City, ServiceType


pytestmark = pytest.mark.integration


@pytest.mark.parametrize("winner", ["approval", "reinstatement"])
def test_new_approval_and_reinstatement_cannot_both_activate_authorization(winner):
    async def prove():
        engine = create_async_engine(require_integration_settings().database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ready = await prepare_handoff_fixture(sessions)
            async with sessions.begin() as session:
                old_app = await command(session, ready, "SUSPEND")
                old_id, old_version = old_app.id, old_app.optimistic_version
                new_app = DriverCityApplication(driver_id=ready.driver_id, city_id=old_app.city_id,
                    requirement_version_id=old_app.requirement_version_id, status="UNDER_REVIEW")
                session.add(new_app)
                await session.flush()
                new_id = new_app.id
                old_evidence = await session.scalar(select(DriverApplicationEvidence).where(
                    DriverApplicationEvidence.application_id == old_id))
                session.add(DriverApplicationEvidence(application_id=new_id,
                    requirement_item_id=old_evidence.requirement_item_id, profile_id=ready.driver_id, status="ACCEPTED"))

            async def execute(session, action):
                if action == "reinstatement":
                    await decide_authorization(session, application_id=old_id, reviewer_user_id=ready.user_id,
                        payload=AuthorizationDecisionRequest(expected_application_version=old_version,
                            action="REINSTATE", reason_code="ELIGIBILITY_REVIEW_PASSED"), now=ready.now)
                else:
                    app = await session.scalar(select(DriverCityApplication).where(DriverCityApplication.id == new_id)
                        .with_for_update().execution_options(populate_existing=True))
                    await decide_application(session, application=app, reviewer_user_id=ready.user_id,
                        payload=ApplicationDecisionRequest(expected_version=1, decision="APPROVE",
                            reason_code="REQUIREMENTS_CONFIRMED", applicant_safe_message="Synthetic reviewed approval.",
                            authorized_service_types=[ServiceType.ON_DEMAND]))
            async def acquire(session):
                await execute(session, winner)
            async def prepare(session):
                return await session.get(DriverCityApplication, old_id), await session.get(DriverCityApplication, new_id)
            async def first(_session):
                return winner
            async def second(session, cached):
                assert cached[1].status.value == "UNDER_REVIEW"
                with pytest.raises(RecruitmentConflict):
                    await execute(session, "reinstatement" if winner == "approval" else "approval")
                return "conflict"
            assert await contended_commands(sessions, acquire_first=acquire, prepare_second=prepare,
                first_command=first, second_command=second) == [winner, "conflict"]
            async with sessions() as session:
                active = list(await session.scalars(select(DriverCityAuthorization).where(
                    DriverCityAuthorization.driver_id == ready.driver_id, DriverCityAuthorization.status == "ACTIVE")))
                assert len(active) == 1
                assert active[0].application_id == (new_id if winner == "approval" else old_id)
                old = await session.get(DriverCityApplication, old_id)
                new = await session.get(DriverCityApplication, new_id)
                assert old.status.value == "APPROVED"
                assert new.status.value == ("APPROVED" if winner == "approval" else "UNDER_REVIEW")
        finally:
            await engine.dispose()
    asyncio.run(prove())


def test_city_restriction_keeps_same_drivers_other_city_eligibility():
    async def prove():
        settings = require_integration_settings()
        second_city_id = await seed_recruiting_test_city(settings, uuid4().hex)
        engine = create_async_engine(settings.database_url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            ready = await prepare_handoff_fixture(sessions)
            async with sessions.begin() as session:
                original = await authorization_for(session, ready)
                first_app = await session.get(DriverCityApplication, original.application_id)
                original_item = await session.scalar(select(DriverRequirementItem).where(
                    DriverRequirementItem.requirement_version_id == first_app.requirement_version_id))
                # Synthetic policy approval and launch state isolate this test
                # from city provisioning, which has its own acceptance suite.
                (await session.get(City, second_city_id)).lifecycle_status = "ACTIVE"
                version = DriverRequirementVersion(city_id=second_city_id, version="synthetic-city-authority-v1",
                    status="ACTIVE", effective_from=ready.now - timedelta(days=1))
                session.add(version)
                await session.flush()
                item = DriverRequirementItem(requirement_version_id=version.id,
                    requirement_code=original_item.requirement_code, evidence_type=original_item.evidence_type,
                    validity_rule_code=original_item.validity_rule_code, required=True,
                    localized_copy_key=original_item.localized_copy_key,
                    localized_label=original_item.localized_label, localized_description=original_item.localized_description)
                app = DriverCityApplication(driver_id=ready.driver_id, city_id=second_city_id,
                    requirement_version_id=version.id, status="APPROVED")
                session.add_all([item, app])
                await session.flush()
                session.add(DriverApplicationEvidence(application_id=app.id, requirement_item_id=item.id,
                    profile_id=ready.driver_id, status="ACCEPTED"))
                authorization = DriverCityAuthorization(driver_id=ready.driver_id, city_id=second_city_id,
                    application_id=app.id, vehicle_id=original.vehicle_id, valid_from=ready.now - timedelta(days=1))
                session.add(authorization)
                await session.flush()
                second_id, first_id = authorization.id, first_app.id
                session.add(DriverCityAuthorizationService(authorization_id=second_id, service_type=ServiceType.ON_DEMAND))
                await decide_authorization(session, application_id=first_id, reviewer_user_id=ready.user_id,
                    payload=AuthorizationDecisionRequest(expected_application_version=first_app.optimistic_version,
                        action="REVOKE", reason_code="OPERATING_PERMISSION_WITHDRAWN"), now=ready.now)
            async with sessions() as session:
                profile = await session.get(DriverProfile, ready.driver_id)
                selected = await select_active_authorization(session, profile=profile, requested_city_id=second_city_id,
                    requested_service_type=ServiceType.ON_DEMAND, now=ready.now)
                assert selected.authorization.id == second_id
                with pytest.raises(RecruitmentConflict):
                    await select_active_authorization(session, profile=profile, requested_city_id=first_app.city_id,
                        requested_service_type=ServiceType.ON_DEMAND, now=ready.now)
        finally:
            await engine.dispose()
    asyncio.run(prove())
