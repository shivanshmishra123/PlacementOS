"""PlacementOS Identity and Institutional Domain Models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from placementos.core.database import Base, TimestampedUUIDModel


class Institution(TimestampedUUIDModel):
    """Institutional tenant boundary representing an academic institution."""

    __tablename__ = "institutions"

    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    memberships: Mapped[list[Membership]] = relationship(
        "Membership", back_populates="institution", cascade="all, delete-orphan"
    )
    student_profiles: Mapped[list[StudentProfile]] = relationship(
        "StudentProfile", back_populates="institution", cascade="all, delete-orphan"
    )


class User(TimestampedUUIDModel):
    """Global user principal identity authenticated via OIDC or dev provider."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    memberships: Mapped[list[Membership]] = relationship(
        "Membership", back_populates="user", cascade="all, delete-orphan"
    )


class Membership(TimestampedUUIDModel):
    """Scoped membership binding a User to an Institution with assigned role and capabilities."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("institution_id", "user_id", name="uq_membership_institution_user"),
        Index("ix_memberships_inst_role", "institution_id", "role"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    institution: Mapped[Institution] = relationship("Institution", back_populates="memberships")
    user: Mapped[User] = relationship("User", back_populates="memberships")
    student_profile: Mapped[StudentProfile | None] = relationship(
        "StudentProfile", back_populates="membership", uselist=False
    )
    drive_assignments: Mapped[list[DriveAssignment]] = relationship(
        "DriveAssignment", back_populates="membership", cascade="all, delete-orphan"
    )


class StudentProfile(TimestampedUUIDModel):
    """Institutional student identity carrying scoped identifier and academic links."""

    __tablename__ = "student_profiles"
    __table_args__ = (
        UniqueConstraint(
            "institution_id", "student_identifier", name="uq_student_institution_identifier"
        ),
        UniqueConstraint("institution_id", "user_id", name="uq_student_institution_user"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    membership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    student_identifier: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    current_academic_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Relationships
    institution: Mapped[Institution] = relationship("Institution", back_populates="student_profiles")
    membership: Mapped[Membership | None] = relationship(
        "Membership", back_populates="student_profile"
    )


class DriveAssignment(TimestampedUUIDModel):
    """Assignment of a coordinator membership to an recruitment drive."""

    __tablename__ = "drive_assignments"
    __table_args__ = (
        Index("ix_drive_assignments_inst_drive", "institution_id", "drive_id"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drive_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    assigned_role: Mapped[str] = mapped_column(
        String(50), default="lead_coordinator", nullable=False
    )

    # Relationships
    membership: Mapped[Membership] = relationship("Membership", back_populates="drive_assignments")


class AuditLog(Base):
    """Immutable audit log recording attributable business events and security actions."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    actor_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
