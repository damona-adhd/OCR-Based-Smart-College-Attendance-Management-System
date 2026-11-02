"""Additive schema for attendance rebuild

Revision ID: 002
Revises: 001
Create Date: 2026-10-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_SETTINGS = [
    ("min_attendance_percentage", "75", "Minimum attendance percentage threshold"),
    ("allow_teacher_create_student", "true", "Allow teachers to add students with name and USN"),
    ("allow_teacher_create_subject", "true", "Allow teachers to add subjects with name and code"),
    ("allow_student_correction_requests", "false", "Allow students to request attendance corrections"),
    ("usn_pattern", "", "Optional regex for USN validation; empty disables extra format checks"),
    ("extraction_provider", "none", "Document extraction provider: none or gemini"),
]


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.add_column("users", sa.Column("full_name", sa.String(200), nullable=True))
    op.add_column("classes", sa.Column("section", sa.String(20), nullable=False, server_default="A"))
    op.add_column("classes", sa.Column("course", sa.String(200), nullable=True))
    op.add_column("students", sa.Column("course", sa.String(200), nullable=True))

    op.add_column(
        "attendance_sessions",
        sa.Column("period", sa.Integer, nullable=False, server_default="1"),
    )
    op.add_column("attendance_sessions", sa.Column("description", sa.String(500), nullable=True))
    op.add_column(
        "attendance_sessions",
        sa.Column("finalized_by_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )

    if dialect == "postgresql":
        op.drop_constraint("uq_session_subject_class_date", "attendance_sessions", type_="unique")
    op.create_unique_constraint(
        "uq_session_subject_class_date_period",
        "attendance_sessions",
        ["subject_id", "class_id", "attendance_date", "period"],
    )

    op.add_column("source_files", sa.Column("checksum", sa.String(64), nullable=True))
    op.add_column("source_files", sa.Column("uploader_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True))
    op.add_column("source_files", sa.Column("purpose", sa.String(50), nullable=True))
    op.create_index("ix_source_files_checksum", "source_files", ["checksum"])

    op.add_column("attendance_records", sa.Column("extraction_confidence", sa.Float, nullable=True))
    op.add_column("attendance_records", sa.Column("match_status", sa.String(30), nullable=True))
    op.add_column(
        "attendance_records",
        sa.Column("is_corrected", sa.Boolean, nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "attendance_corrections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "attendance_record_id",
            sa.Integer,
            sa.ForeignKey("attendance_records.id"),
            nullable=False,
        ),
        sa.Column("previous_status", sa.String(20), nullable=False),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("actor_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_attendance_corrections_record", "attendance_corrections", ["attendance_record_id"])

    op.create_table(
        "attendance_correction_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("students.id"), nullable=False),
        sa.Column(
            "attendance_record_id",
            sa.Integer,
            sa.ForeignKey("attendance_records.id"),
            nullable=False,
        ),
        sa.Column("requested_status", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "rejected", name="correctionrequeststatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("reviewer_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_note", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_correction_requests_student", "attendance_correction_requests", ["student_id"])

    settings = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.String),
        sa.column("description", sa.String),
    )
    for key, value, description in DEFAULT_SETTINGS:
        op.execute(
            sa.text(
                "INSERT INTO app_settings (key, value, description) "
                "SELECT :key, :value, :description "
                "WHERE NOT EXISTS (SELECT 1 FROM app_settings WHERE key = :key)"
            ).bindparams(key=key, value=value, description=description)
        )


def downgrade() -> None:
    op.drop_table("attendance_correction_requests")
    op.drop_table("attendance_corrections")
    op.drop_column("attendance_records", "is_corrected")
    op.drop_column("attendance_records", "match_status")
    op.drop_column("attendance_records", "extraction_confidence")
    op.drop_index("ix_source_files_checksum", table_name="source_files")
    op.drop_column("source_files", "purpose")
    op.drop_column("source_files", "uploader_id")
    op.drop_column("source_files", "checksum")
    op.drop_constraint("uq_session_subject_class_date_period", "attendance_sessions", type_="unique")
    op.create_unique_constraint(
        "uq_session_subject_class_date",
        "attendance_sessions",
        ["subject_id", "class_id", "attendance_date"],
    )
    op.drop_column("attendance_sessions", "finalized_by_user_id")
    op.drop_column("attendance_sessions", "description")
    op.drop_column("attendance_sessions", "period")
    op.drop_column("students", "course")
    op.drop_column("classes", "course")
    op.drop_column("classes", "section")
    op.drop_column("users", "full_name")
    op.execute("DROP TYPE IF EXISTS correctionrequeststatus")
