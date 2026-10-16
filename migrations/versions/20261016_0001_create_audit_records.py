"""Create persisted audit record table."""

from alembic import op
import sqlalchemy as sa

revision = "20261016_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_records",
        sa.Column("audit_id", sa.String(length=36), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_level", sa.String(length=10), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_rationale", sa.String(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("tools_used", sa.JSON(), nullable=False),
        sa.Column("trace", sa.JSON(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("disclaimer", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_audit_records_risk_level", "audit_records", ["risk_level"], unique=False)
    op.create_index("ix_audit_records_created_id", "audit_records", ["created_at", "audit_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_records_created_id", table_name="audit_records")
    op.drop_index("ix_audit_records_risk_level", table_name="audit_records")
    op.drop_table("audit_records")
