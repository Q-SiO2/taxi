"""Transactional document-evidence changes for city driver applications."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.driver_applications.models import (
    ApplicationEvidenceStatus,
    DocumentScanStatus,
    DriverApplicationDocument,
    DriverApplicationEvidence,
    DriverCityApplication,
    DriverRequirementItem,
    RequirementEvidenceType,
)
from taximobile_api.domains.driver_applications.service import (
    ApplicationReferenceInvalid,
    EDITABLE_APPLICATION_STATUSES,
    RecruitmentConflict,
    RecruitmentNotFound,
    require_expected_version,
)
from taximobile_api.integrations.driver_documents import StoredDriverDocument


async def require_document_item(
    session: AsyncSession,
    application: DriverCityApplication,
    requirement_item_id: UUID,
) -> DriverRequirementItem:
    item = await session.scalar(
        select(DriverRequirementItem).where(
            DriverRequirementItem.id == requirement_item_id,
            DriverRequirementItem.requirement_version_id
            == application.requirement_version_id,
        )
    )
    if item is None:
        raise ApplicationReferenceInvalid(
            "The document requirement does not belong to this application version."
        )
    if item.evidence_type != RequirementEvidenceType.DOCUMENT:
        raise ApplicationReferenceInvalid(
            "The selected requirement does not accept document evidence."
        )
    return item


async def preflight_document_change(
    session: AsyncSession,
    application: DriverCityApplication,
    *,
    requirement_item_id: UUID,
    expected_version: int,
) -> None:
    if application.status not in EDITABLE_APPLICATION_STATUSES:
        raise RecruitmentConflict("This application is not editable in its current status.")
    require_expected_version(application.optimistic_version, expected_version)
    await require_document_item(session, application, requirement_item_id)


async def attach_clean_document(
    session: AsyncSession,
    application: DriverCityApplication,
    *,
    requirement_item_id: UUID,
    expected_version: int,
    stored: StoredDriverDocument,
    retention_days: int,
) -> tuple[DriverApplicationDocument, str | None]:
    await preflight_document_change(
        session,
        application,
        requirement_item_id=requirement_item_id,
        expected_version=expected_version,
    )
    now = datetime.now(UTC)
    evidence = await session.scalar(
        select(DriverApplicationEvidence)
        .where(
            DriverApplicationEvidence.application_id == application.id,
            DriverApplicationEvidence.requirement_item_id == requirement_item_id,
        )
        .with_for_update()
    )
    replaced_key: str | None = None
    if evidence is not None and evidence.document_id is not None:
        replaced = await session.scalar(
            select(DriverApplicationDocument)
            .where(DriverApplicationDocument.id == evidence.document_id)
            .with_for_update()
        )
        if replaced is not None and replaced.deleted_at is None:
            replaced.deleted_at = now
            replaced_key = replaced.opaque_storage_key

    document = DriverApplicationDocument(
        application_id=application.id,
        requirement_item_id=requirement_item_id,
        opaque_storage_key=stored.opaque_storage_key,
        media_type=stored.media_type,
        byte_size=stored.byte_size,
        sha256=stored.sha256,
        malware_scan_status=DocumentScanStatus.CLEAN,
        uploaded_at=now,
        retention_deadline=now + timedelta(days=retention_days),
    )
    session.add(document)
    await session.flush()
    if evidence is None:
        evidence = DriverApplicationEvidence(
            application_id=application.id,
            requirement_item_id=requirement_item_id,
        )
        session.add(evidence)
    evidence.profile_id = None
    evidence.vehicle_id = None
    evidence.credential_id = None
    evidence.document_id = document.id
    evidence.status = ApplicationEvidenceStatus.PENDING
    application.optimistic_version += 1
    application.updated_at = now
    await session.flush()
    return document, replaced_key


async def remove_document(
    session: AsyncSession,
    application: DriverCityApplication,
    *,
    document_id: UUID,
    expected_version: int,
) -> DriverApplicationDocument:
    if application.status not in EDITABLE_APPLICATION_STATUSES:
        raise RecruitmentConflict("This application is not editable in its current status.")
    require_expected_version(application.optimistic_version, expected_version)
    document = await session.scalar(
        select(DriverApplicationDocument)
        .where(
            DriverApplicationDocument.id == document_id,
            DriverApplicationDocument.application_id == application.id,
            DriverApplicationDocument.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if document is None:
        raise RecruitmentNotFound("Driver application document not found.")
    await session.execute(
        delete(DriverApplicationEvidence).where(
            DriverApplicationEvidence.application_id == application.id,
            DriverApplicationEvidence.document_id == document.id,
        )
    )
    now = datetime.now(UTC)
    document.deleted_at = now
    application.optimistic_version += 1
    application.updated_at = now
    await session.flush()
    return document
