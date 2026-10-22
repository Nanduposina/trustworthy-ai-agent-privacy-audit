"""Store optional Gemini assessments on audit reports."""

from alembic import op
import sqlalchemy as sa

revision = "20261016_0002"
down_revision = "20261016_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_records", sa.Column("ai_analysis", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_records", "ai_analysis")
