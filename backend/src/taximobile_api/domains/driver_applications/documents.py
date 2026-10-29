"""Transactional document-evidence changes for city driver applications."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import blake2b
from uuid import UUID

from sqlalchemy import delete, select, text
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


UPLOAD_LEASE_SECONDS = 300


async def lock_document_key(session: AsyncSession, key: str, *, wait: bool = True) -> bool:
    """Serialize upload registration with orphan recheck/delete, even for no row.

    A stable domain-separated 64-bit hash reveals no object key in pg_locks.
    A hash collision only serializes unrelated work. Transaction exit releases it.
    """
    digest = blake2b(key.encode("ascii"), digest_size=8, person=b"tm-doc-key-v1").digest()
    lock_id = int.from_bytes(digest, "big", signed=True)
    if wait:
        await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
        return True
    return bool(await session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock_id}))


async def reserve_document_upload(
    session: AsyncSession,
    application: DriverCityApplication,
    *,
    requirement_item_id: UUID,
    expected_version: int,
    stored: StoredDriverDocument,
    retention_days: int,
) -> DriverApplicationDocument:
    """Commit hidden cleanup authority before any bytes are published."""
    await preflight_document_change(session, application,
                                    requirement_item_id=requirement_item_id,
                                    expected_version=expected_version)
    await lock_document_key(session, stored.opaque_storage_key)
    now = datetime.now(UTC)
    document = DriverApplicationDocument(
        application_id=application.id,
        requirement_item_id=requirement_item_id,
        opaque_storage_key=stored.opaque_storage_key,
        media_type=stored.media_type,
        byte_size=stored.byte_size,
        sha256=stored.sha256,
        malware_scan_status=DocumentScanStatus.CLEAN,
        uploaded_at=now,
        deleted_at=now,
        upload_lease_until=now + timedelta(seconds=UPLOAD_LEASE_SECONDS),
        retention_deadline=now + timedelta(days=retention_days),
    )
    session.add(document)
    await session.flush()
    return document


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
    document_id: UUID,
) -> tuple[DriverApplicationDocument, str | None]:
    await preflight_document_change(
        session,
        application,
        requirement_item_id=requirement_item_id,
        expected_version=expected_version,
    )
    document = await session.scalar(
        select(DriverApplicationDocument).where(
            DriverApplicationDocument.id == document_id,
            DriverApplicationDocument.application_id == application.id,
            DriverApplicationDocument.requirement_item_id == requirement_item_id,
        ).with_for_update()
    )
    if (document is None or document.upload_lease_until is None
            or document.deleted_at is None
            or document.malware_scan_status != DocumentScanStatus.CLEAN):
        raise RecruitmentConflict("The document upload lease expired; upload the document again.")
    evidence = await session.scalar(
        select(DriverApplicationEvidence)
        .where(
            DriverApplicationEvidence.application_id == application.id,
            DriverApplicationEvidence.requirement_item_id == requirement_item_id,
        )
        .with_for_update()
    )
    replaced_key: str | None = None
    replaced: DriverApplicationDocument | None = None
    if evidence is not None and evidence.document_id is not None:
        replaced = await session.scalar(
            select(DriverApplicationDocument)
            .where(DriverApplicationDocument.id == evidence.document_id)
            .with_for_update()
        )

    # All document/evidence/replacement locks may wait. Read the clock only
    # after acquiring them, immediately before the activation decision.
    now = datetime.now(UTC)
    if document.upload_lease_until <= now:
        raise RecruitmentConflict("The document upload lease expired; upload the document again.")
    if replaced is not None and replaced.deleted_at is None:
        replaced.deleted_at = now
        replaced_key = replaced.opaque_storage_key

    document.deleted_at = None
    document.upload_lease_until = None
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
