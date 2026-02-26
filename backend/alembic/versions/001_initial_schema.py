"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("project_id", sa.UUID(as_uuid=False), primary_key=True),
        sa.Column("inn_en", sa.String, nullable=False),
        sa.Column("inn_ru", sa.String, nullable=True),
        sa.Column("dosage", sa.String, nullable=False),
        sa.Column("shape", sa.String, nullable=True),
        sa.Column("drug_name_t", sa.String, nullable=True),
        sa.Column("drug_name_r", sa.String, nullable=True),
        sa.Column("status", sa.String),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
        sa.Column("search_results", sa.JSON, nullable=True),
        sa.Column("design_parameters", sa.JSON, nullable=True),
        sa.Column("regulatory_check", sa.JSON, nullable=True),
    )

    op.create_table(
        "drug_parameters",
        sa.Column("param_id", sa.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("parameter", sa.String, nullable=False),
        sa.Column("value", sa.String, nullable=False),
        sa.Column("unit", sa.String, nullable=True),
        sa.Column("source_pmid", sa.String, nullable=True),
        sa.Column("source_title", sa.String, nullable=True),
        sa.Column("is_reliable", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table("drug_parameters")
    op.drop_table("projects")
