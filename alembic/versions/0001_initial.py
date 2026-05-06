"""initial schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "urls",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("short_code", sa.String(length=7), nullable=False),
        sa.Column("original_url", sa.String(length=2048), nullable=False),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_urls_owner_id"), "urls", ["owner_id"], unique=False)
    op.create_index(op.f("ix_urls_short_code"), "urls", ["short_code"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_urls_short_code"), table_name="urls")
    op.drop_index(op.f("ix_urls_owner_id"), table_name="urls")
    op.drop_table("urls")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
