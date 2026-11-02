"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-10-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "lecturer", "student", name="userrole"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── departments ────────────────────────────────────────
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
    )
    op.create_index("ix_departments_code", "departments", ["code"])

    # ── classes ────────────────────────────────────────────
    op.create_table(
        "classes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("academic_year", sa.String(20), nullable=False),
        sa.Column("semester", sa.Integer, nullable=False),
        sa.Column(
            "department_id", sa.Integer,
            sa.ForeignKey("departments.id"), nullable=False,
        ),
    )

    # ── subjects ───────────────────────────────────────────
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("subject_code", sa.String(50), nullable=False, unique=True),
        sa.Column("subject_name", sa.String(200), nullable=False),
        sa.Column("semester", sa.Integer, nullable=False),
        sa.Column(
            "department_id", sa.Integer,
            sa.ForeignKey("departments.id"), nullable=False,
        ),
    )
    op.create_index("ix_subjects_subject_code", "subjects", ["subject_code"])

    # ── students ───────────────────────────────────────────
    op.create_table(
        "students",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id", sa.Integer,
            sa.ForeignKey("users.id"), nullable=True, unique=True,
        ),
        sa.Column("usn", sa.String(50), nullable=False, unique=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column(
            "department_id", sa.Integer,
            sa.ForeignKey("departments.id"), nullable=False,
        ),
        sa.Column("academic_year", sa.String(20), nullable=False),
        sa.Column("semester", sa.Integer, nullable=False),
        sa.Column(
            "class_id", sa.Integer,
            sa.ForeignKey("classes.id"), nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
    )
    op.create_index("ix_students_usn", "students", ["usn"])

    # ── lecturers ──────────────────────────────────────────
    op.create_table(
        "lecturers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id", sa.Integer,
            sa.ForeignKey("users.id"), nullable=False, unique=True,
        ),
        sa.Column("employee_id", sa.String(50), nullable=False, unique=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column(
            "department_id", sa.Integer,
            sa.ForeignKey("departments.id"), nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
    )
    op.create_index("ix_lecturers_employee_id", "lecturers", ["employee_id"])

    # ── teaching_assignments ───────────────────────────────
    op.create_table(
        "teaching_assignments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "lecturer_id", sa.Integer,
            sa.ForeignKey("lecturers.id"), nullable=False,
        ),
        sa.Column(
            "subject_id", sa.Integer,
            sa.ForeignKey("subjects.id"), nullable=False,
        ),
        sa.Column(
            "class_id", sa.Integer,
            sa.ForeignKey("classes.id"), nullable=False,
        ),
        sa.UniqueConstraint("lecturer_id", "subject_id", "class_id", name="uq_assignment"),
    )

    # ── source_files  (no FK to attendance_sessions yet — added via ALTER below)
    op.create_table(
        "source_files",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("attendance_session_id", sa.Integer, nullable=True),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column(
            "processing_status",
            sa.Enum(
                "pending", "processing", "completed", "failed",
                name="processingstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── attendance_sessions  (FK to source_files added via ALTER below)
    op.create_table(
        "attendance_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "subject_id", sa.Integer,
            sa.ForeignKey("subjects.id"), nullable=False,
        ),
        sa.Column(
            "class_id", sa.Integer,
            sa.ForeignKey("classes.id"), nullable=False,
        ),
        sa.Column(
            "lecturer_id", sa.Integer,
            sa.ForeignKey("lecturers.id"), nullable=False,
        ),
        sa.Column("attendance_date", sa.Date, nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "finalized", "cancelled", name="sessionstatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "source_type",
            sa.Enum("manual", "ocr", name="sourcetype"),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("source_file_id", sa.Integer, nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "subject_id", "class_id", "attendance_date",
            name="uq_session_subject_class_date",
        ),
    )

    # Now add both circular FKs via ALTER (PostgreSQL supports this; SQLite does not but that's test-only)
    op.create_foreign_key(
        "fk_sessions_source_file",
        "attendance_sessions", "source_files",
        ["source_file_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_source_files_session",
        "source_files", "attendance_sessions",
        ["attendance_session_id"], ["id"],
    )

    # ── attendance_records ─────────────────────────────────
    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "attendance_session_id", sa.Integer,
            sa.ForeignKey("attendance_sessions.id"), nullable=False,
        ),
        sa.Column(
            "student_id", sa.Integer,
            sa.ForeignKey("students.id"), nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("present", "absent", name="attendancestatus"),
            nullable=False,
        ),
        sa.Column(
            "source_type",
            sa.Enum("manual", "ocr", name="sourcetype"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "attendance_session_id", "student_id",
            name="uq_record_session_student",
        ),
    )

    # ── audit_events ───────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "actor_user_id", sa.Integer,
            sa.ForeignKey("users.id"), nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.Integer, nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    # ── app_settings ───────────────────────────────────────
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
    )
    op.create_index("ix_app_settings_key", "app_settings", ["key"])


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("audit_events")
    op.drop_table("attendance_records")
    op.drop_constraint("fk_sessions_source_file", "attendance_sessions", type_="foreignkey")
    op.drop_constraint("fk_source_files_session", "source_files", type_="foreignkey")
    op.drop_table("attendance_sessions")
    op.drop_table("source_files")
    op.drop_table("teaching_assignments")
    op.drop_table("lecturers")
    op.drop_table("students")
    op.drop_table("subjects")
    op.drop_table("classes")
    op.drop_table("departments")
    op.drop_table("users")
    for enum_name in [
        "userrole", "processingstatus", "sessionstatus",
        "sourcetype", "attendancestatus",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
