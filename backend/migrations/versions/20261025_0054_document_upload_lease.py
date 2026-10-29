"""Keep recoverable metadata before protected document publication.

Revision ID: 20261025_0054
Revises: 20261023_0053
"""

from alembic import op
import sqlalchemy as sa

revision = "20261025_0054"
down_revision = "20261023_0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("driver_application_documents",
                  sa.Column("upload_lease_until", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("driver_document_upload_lease", "driver_application_documents",
                              "upload_lease_until IS NULL OR "
                              "(deleted_at IS NOT NULL AND upload_lease_until > uploaded_at)")
    op.drop_constraint("driver_document_retention_reason", "driver_document_retention_actions", type_="check")
    op.create_check_constraint("driver_document_retention_reason", "driver_document_retention_actions",
                              "reason IN ('APPLICANT_DELETED', 'RETENTION_EXPIRED', 'UPLOAD_UNCOMMITTED')")


def downgrade() -> None:
    # Neither unknown upload outcomes nor immutable erasure history may be
    # silently lost to make an older binary start successfully.
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM driver_application_documents WHERE upload_lease_until IS NOT NULL)
         OR EXISTS (SELECT 1 FROM driver_document_retention_actions WHERE reason = 'UPLOAD_UNCOMMITTED')
      THEN RAISE EXCEPTION 'Document upload recovery or erasure evidence prevents downgrade';
      END IF;
    END $$""")
    op.drop_constraint("driver_document_retention_reason", "driver_document_retention_actions", type_="check")
    op.create_check_constraint("driver_document_retention_reason", "driver_document_retention_actions",
                              "reason IN ('APPLICANT_DELETED', 'RETENTION_EXPIRED')")
    op.drop_constraint("driver_document_upload_lease", "driver_application_documents", type_="check")
    op.drop_column("driver_application_documents", "upload_lease_until")
