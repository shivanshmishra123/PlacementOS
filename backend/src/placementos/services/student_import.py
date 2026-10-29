"""PlacementOS Student CSV Import and Preview Service (P02-T05)."""

from __future__ import annotations

import csv
import decimal
import io
import json
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.errors import BadRequestException
from placementos.core.redis import get_redis_client
from placementos.models.academic import AcademicRecordRevision
from placementos.models.identity import AuditLog, Membership, StudentProfile, User


@dataclass
class ParsedStudentRow:
    row_number: int
    student_identifier: str
    full_name: str
    email: str
    branch: str
    cgpa: str  # stored as string for exact Decimal serialization
    scale: str
    graduation_year: int
    active_backlogs: int | None  # None = missing/unknown; 0 = clean; >0 = active
    history_backlogs: int | None
    is_valid: bool
    error_message: str | None = None
    is_new: bool = True


@dataclass
class ImportPreviewReport:
    preview_token: str
    total_rows: int
    valid_rows_count: int
    invalid_rows_count: int
    new_students_count: int
    updating_students_count: int
    sample_rows: list[dict[str, Any]]
    invalid_rows: list[dict[str, Any]]


class StudentImportService:
    """Service handling CSV validation, preview without mutation, and idempotent commit."""

    HEADER_ALIASES = {
        "student_identifier": ["student_identifier", "roll_number", "roll_no", "usn", "reg_no", "identifier"],
        "full_name": ["full_name", "name", "student_name", "candidate_name"],
        "email": ["email", "student_email", "college_email"],
        "branch": ["branch", "dept", "department", "major", "stream"],
        "cgpa": ["cgpa", "gpa", "grade_point"],
        "scale": ["scale", "max_cgpa", "grading_scale", "base"],
        "graduation_year": ["graduation_year", "grad_year", "batch", "passing_year", "cohort"],
        "active_backlogs": ["active_backlogs", "backlogs", "current_backlogs", "active_backlog"],
        "history_backlogs": ["history_backlogs", "total_backlogs", "past_backlogs"],
    }

    @classmethod
    def _map_headers(cls, raw_headers: Sequence[str]) -> dict[str, str]:
        """Map raw CSV headers to canonical field names."""
        mapping: dict[str, str] = {}
        for raw in raw_headers:
            cleaned = raw.strip().lower().replace(" ", "_").replace("-", "_")
            for canonical, aliases in cls.HEADER_ALIASES.items():
                if cleaned in aliases or cleaned == canonical:
                    mapping[canonical] = raw
                    break
        return mapping

    @classmethod
    async def preview_csv(
        cls,
        institution_id: uuid.UUID,
        csv_text: str,
        db: AsyncSession,
    ) -> ImportPreviewReport:
        """Parse and validate CSV rows without making any database mutations."""
        f = io.StringIO(csv_text.strip())
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise BadRequestException("Empty CSV or missing header row")

        header_map = cls._map_headers(reader.fieldnames)
        missing_required = []
        for req in ["student_identifier", "full_name", "email", "branch", "cgpa", "graduation_year"]:
            if req not in header_map:
                missing_required.append(req)

        if missing_required:
            raise BadRequestException(
                f"Missing required CSV columns: {', '.join(missing_required)}",
                details={"detected_headers": reader.fieldnames, "missing": missing_required},
            )

        # Query existing identifiers in institution to distinguish new vs updating
        existing_res = await db.execute(
            select(StudentProfile.student_identifier).where(
                StudentProfile.institution_id == institution_id
            )
        )
        existing_identifiers = set(existing_res.scalars().all())

        parsed_rows: list[ParsedStudentRow] = []
        row_num = 1
        new_count = 0
        updating_count = 0

        for row in reader:
            row_num += 1
            # Extract raw values
            raw_id = (row.get(header_map["student_identifier"]) or "").strip()
            raw_name = (row.get(header_map["full_name"]) or "").strip()
            raw_email = (row.get(header_map["email"]) or "").strip().lower()
            raw_branch = (row.get(header_map["branch"]) or "").strip().upper()
            raw_cgpa = (row.get(header_map["cgpa"]) or "").strip()
            raw_scale = (row.get(header_map.get("scale", "")) or "10.00").strip()
            raw_grad = (row.get(header_map["graduation_year"]) or "").strip()
            raw_backlog = (row.get(header_map.get("active_backlogs", "")) or "").strip()
            raw_hist_backlog = (row.get(header_map.get("history_backlogs", "")) or "").strip()

            error_msg: str | None = None
            is_valid = True

            if not raw_id:
                is_valid = False
                error_msg = "Student identifier cannot be empty"
            elif not raw_email or "@" not in raw_email:
                is_valid = False
                error_msg = f"Invalid email address: {raw_email}"
            elif not raw_branch:
                is_valid = False
                error_msg = "Branch cannot be empty"

            # Parse CGPA with exact decimal arithmetic (INV-05)
            cgpa_dec = decimal.Decimal("0.00")
            scale_dec = decimal.Decimal("10.00")
            if is_valid:
                try:
                    cgpa_dec = decimal.Decimal(raw_cgpa)
                    scale_dec = decimal.Decimal(raw_scale)
                    if cgpa_dec < 0 or cgpa_dec > scale_dec:
                        is_valid = False
                        error_msg = f"CGPA {cgpa_dec} exceeds scale [0, {scale_dec}]"
                except (decimal.InvalidOperation, ValueError):
                    is_valid = False
                    error_msg = f"Invalid numerical CGPA or scale: '{raw_cgpa}'"

            # Parse graduation year
            grad_year = 0
            if is_valid:
                try:
                    grad_year = int(raw_grad)
                    if grad_year < 2000 or grad_year > 2100:
                        is_valid = False
                        error_msg = f"Graduation year out of range: {grad_year}"
                except ValueError:
                    is_valid = False
                    error_msg = f"Invalid graduation year: '{raw_grad}'"

            # Parse backlogs (None differs from 0 - INV-02)
            active_backlogs: int | None = None
            if is_valid and raw_backlog:
                try:
                    active_backlogs = int(raw_backlog)
                    if active_backlogs < 0:
                        is_valid = False
                        error_msg = "Active backlogs cannot be negative"
                except ValueError:
                    is_valid = False
                    error_msg = f"Invalid active backlogs integer: '{raw_backlog}'"

            hist_backlogs: int | None = None
            if is_valid and raw_hist_backlog:
                try:
                    hist_backlogs = int(raw_hist_backlog)
                except ValueError:
                    pass

            is_new = raw_id not in existing_identifiers
            if is_valid:
                if is_new:
                    new_count += 1
                else:
                    updating_count += 1

            parsed_rows.append(
                ParsedStudentRow(
                    row_number=row_num,
                    student_identifier=raw_id,
                    full_name=raw_name,
                    email=raw_email,
                    branch=raw_branch,
                    cgpa=str(cgpa_dec),
                    scale=str(scale_dec),
                    graduation_year=grad_year,
                    active_backlogs=active_backlogs,
                    history_backlogs=hist_backlogs,
                    is_valid=is_valid,
                    error_message=error_msg,
                    is_new=is_new,
                )
            )

        # Generate preview token and cache in Redis for 1 hour
        preview_token = f"import_preview:{uuid.uuid4()}"
        redis = get_redis_client()
        cache_payload = {
            "institution_id": str(institution_id),
            "rows": [asdict(r) for r in parsed_rows if r.is_valid],
            "created_at": datetime.now(UTC).isoformat(),
        }
        await redis.set(preview_token, json.dumps(cache_payload), ex=3600)

        valid_rows = [asdict(r) for r in parsed_rows if r.is_valid]
        invalid_rows = [asdict(r) for r in parsed_rows if not r.is_valid]

        return ImportPreviewReport(
            preview_token=preview_token,
            total_rows=len(parsed_rows),
            valid_rows_count=len(valid_rows),
            invalid_rows_count=len(invalid_rows),
            new_students_count=new_count,
            updating_students_count=updating_count,
            sample_rows=valid_rows[:10],
            invalid_rows=invalid_rows,
        )

    @classmethod
    async def commit_preview(
        cls,
        preview_token: str,
        institution_id: uuid.UUID,
        committer_membership_id: uuid.UUID,
        committer_user_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Commit previewed rows into verified student records and append immutable revisions."""
        redis = get_redis_client()
        raw_cache = await redis.get(preview_token)
        if not raw_cache:
            raise BadRequestException(
                "Import preview expired or invalid. Please re-upload CSV."
            )

        cached_data = json.loads(raw_cache)
        if cached_data.get("institution_id") != str(institution_id):
            raise BadRequestException("Preview token belongs to a different institution.")

        rows_data = cached_data.get("rows", [])
        if not rows_data:
            raise BadRequestException("No valid rows to commit.")

        created_count = 0
        updated_count = 0

        for r in rows_data:
            identifier = r["student_identifier"]
            email = r["email"]
            full_name = r["full_name"]
            branch = r["branch"]
            cgpa = decimal.Decimal(r["cgpa"])
            scale = decimal.Decimal(r["scale"])
            grad_year = r["graduation_year"]
            active_backlogs = r["active_backlogs"]
            hist_backlogs = r["history_backlogs"]

            # 1. Upsert User
            user_res = await db.execute(select(User).where(User.email == email))
            user = user_res.scalar_one_or_none()
            if not user:
                user = User(email=email, full_name=full_name)
                db.add(user)
                await db.flush()

            # 2. Ensure Student Membership
            mem_res = await db.execute(
                select(Membership).where(
                    Membership.institution_id == institution_id,
                    Membership.user_id == user.id,
                )
            )
            membership = mem_res.scalar_one_or_none()
            if not membership:
                membership = Membership(
                    institution_id=institution_id,
                    user_id=user.id,
                    role="student",
                    capabilities=["student:portal", "registration:submit", "correction:propose"],
                )
                db.add(membership)
                await db.flush()

            # 3. Upsert Student Profile
            profile_res = await db.execute(
                select(StudentProfile).where(
                    StudentProfile.institution_id == institution_id,
                    StudentProfile.student_identifier == identifier,
                )
            )
            profile = profile_res.scalar_one_or_none()

            if not profile:
                profile = StudentProfile(
                    institution_id=institution_id,
                    user_id=user.id,
                    membership_id=membership.id,
                    student_identifier=identifier,
                )
                db.add(profile)
                await db.flush()
                created_count += 1
                rev_num = 1
            else:
                updated_count += 1
                # Find current latest revision number
                latest_rev_res = await db.execute(
                    select(AcademicRecordRevision.revision_number)
                    .where(AcademicRecordRevision.student_profile_id == profile.id)
                    .order_by(AcademicRecordRevision.revision_number.desc())
                    .limit(1)
                )
                latest_rev = latest_rev_res.scalar_one_or_none() or 0
                rev_num = latest_rev + 1

            # 4. Insert Verified Academic Revision
            now = datetime.now(UTC)
            revision = AcademicRecordRevision(
                institution_id=institution_id,
                student_profile_id=profile.id,
                revision_number=rev_num,
                source="csv_import",
                source_reference=preview_token,
                is_verified=True,
                verified_at=now,
                verified_by_membership_id=committer_membership_id,
                branch=branch,
                cgpa=cgpa,
                cgpa_scale=scale,
                graduation_year=grad_year,
                active_backlogs=active_backlogs,
                history_backlogs=hist_backlogs,
            )
            db.add(revision)
            await db.flush()

            # Update pointer on student profile to latest verified revision
            profile.current_academic_revision_id = revision.id
            await db.flush()

        # 5. Record AuditLog
        audit = AuditLog(
            institution_id=institution_id,
            actor_user_id=committer_user_id,
            actor_membership_id=committer_membership_id,
            action="student:import_commit",
            target_type="student_cohort",
            target_id=str(institution_id),
            payload={
                "preview_token": preview_token,
                "created_count": created_count,
                "updated_count": updated_count,
                "total_committed": len(rows_data),
            },
        )
        db.add(audit)
        # Any committed roster or verified-record change invalidates current projections.
        from placementos.services.eligibility_runs import EligibilityRunService

        await EligibilityRunService.mark_institution_runs_stale(
            db, institution_id, committer_membership_id
        )
        await db.commit()

        # Invalidate preview token in Redis
        await redis.delete(preview_token)

        return {
            "message": "Student records successfully committed",
            "created_students": created_count,
            "updated_students": updated_count,
            "total_committed": len(rows_data),
        }
