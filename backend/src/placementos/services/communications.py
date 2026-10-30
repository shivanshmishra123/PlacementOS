"""P07 deterministic drafting, audience freezing, and proposal fingerprints."""

from __future__ import annotations

import string
import uuid
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import settings
from placementos.core.errors import BadRequestException, ConflictException
from placementos.models.communications import (
    AudienceRecipient,
    AudienceSnapshot,
    CommunicationDraft,
)
from placementos.models.eligibility import EligibilityResult, EvaluationRun
from placementos.models.identity import Institution, StudentProfile, User
from placementos.models.intelligence import ActionProposal
from placementos.models.participation import Registration
from placementos.models.recruitment import Company, Drive, DriveRevision
from placementos.schemas.communications import CommunicationDraftCreate
from placementos.services.eligibility_engine import canonical_hash
from placementos.services.participation import compute_readiness
from placementos.services.session import AuthContext

TEMPLATE_VERSION = "communications-v1"
ALLOWED_FIELDS = {
    "student_name",
    "company_name",
    "role_title",
    "registration_link",
    "registration_deadline",
    "timezone",
    "required_documents",
    "reply_to",
}
DEFAULT_TEMPLATES: dict[str, tuple[str, str]] = {
    "drive_announcement": (
        "{company_name}: {role_title} placement drive",
        "Hello {student_name},\n\nYou are eligible to register for the {role_title} opportunity at "
        "{company_name}. Register at {registration_link} before {registration_deadline} "
        "({timezone}).\n\nFor support, contact {reply_to}.\n",
    ),
    "registration_deadline_reminder": (
        "Reminder: register for {company_name} before {registration_deadline}",
        "Hello {student_name},\n\nRegistration for {role_title} at {company_name} closes at "
        "{registration_deadline} ({timezone}). Register at {registration_link}.\n\n"
        "For support, contact {reply_to}.\n",
    ),
    "missing_document_reminder": (
        "Action required: documents for {company_name}",
        "Hello {student_name},\n\nYour required documents for {role_title} at {company_name} "
        "need attention: {required_documents}. Open {registration_link} to review them.\n\n"
        "For support, contact {reply_to}.\n",
    ),
    "clarification": (
        "Information about {company_name}: {role_title}",
        "Hello {student_name},\n\nThis is a clarification for the {role_title} opportunity at "
        "{company_name}. Review the current drive information at {registration_link}.\n\n"
        "For support, contact {reply_to}.\n",
    ),
}


def sender_connection_revision() -> str:
    """Fingerprint non-secret transport identity used in the approval dependency."""
    return canonical_hash(
        {
            "adapter_mode": settings.EMAIL_ADAPTER_MODE,
            "smtp_host": settings.SMTP_HOST,
            "smtp_port": settings.SMTP_PORT,
            "sender": settings.SMTP_SENDER.lower(),
        }
    )


def contact_revision(user: User) -> str:
    return canonical_hash(
        {
            "user_id": str(user.id),
            "email": user.email.strip().lower(),
            "updated_at": user.updated_at.isoformat(),
        }
    )


def _template_fields(value: str) -> set[str]:
    fields: set[str] = set()
    try:
        for _, field_name, _, _ in string.Formatter().parse(value):
            if field_name:
                fields.add(field_name)
    except ValueError as exc:
        raise BadRequestException(f"Invalid message template: {exc}") from exc
    unknown = fields - ALLOWED_FIELDS
    if unknown:
        raise BadRequestException(f"Unsupported template variables: {', '.join(sorted(unknown))}")
    return fields


def validate_templates(kind: str, subject: str, body: str) -> None:
    fields = _template_fields(subject) | _template_fields(body)
    required = {"student_name", "company_name", "role_title", "reply_to"}
    if kind in {"drive_announcement", "registration_deadline_reminder"}:
        required |= {"registration_link", "registration_deadline", "timezone"}
    if kind == "missing_document_reminder":
        required |= {"required_documents", "registration_link"}
    missing = required - fields
    if missing:
        raise BadRequestException(
            f"The {kind} template is missing required variables: {', '.join(sorted(missing))}"
        )


def render_template(template: str, merge_data: dict[str, str]) -> str:
    try:
        return template.format_map(merge_data)
    except (KeyError, ValueError) as exc:
        raise BadRequestException(
            f"Message could not be rendered from approved facts: {exc}"
        ) from exc


async def create_frozen_draft(
    session: AsyncSession,
    auth: AuthContext,
    drive: Drive,
    payload: CommunicationDraftCreate,
) -> tuple[CommunicationDraft, AudienceSnapshot, list[AudienceRecipient]]:
    if (
        drive.status != "published"
        or not drive.published_drive_revision_id
        or not drive.published_evaluation_run_id
    ):
        raise ConflictException("Communication drafting requires a published drive and evaluation")
    evaluation = await session.get(EvaluationRun, drive.published_evaluation_run_id)
    if not evaluation or evaluation.status != "completed" or evaluation.is_stale:
        raise ConflictException("Communication drafting requires a current completed evaluation")
    revision = await session.get(DriveRevision, drive.published_drive_revision_id)
    institution = await session.get(Institution, drive.institution_id)
    company = await session.get(Company, drive.company_id)
    if not revision or not institution or not company or not revision.registration_end_at:
        raise ConflictException("Published drive facts are incomplete")

    default_subject, default_body = DEFAULT_TEMPLATES[payload.communication_kind]
    subject = payload.subject_template or default_subject
    body = payload.body_template or default_body
    validate_templates(payload.communication_kind, subject, body)
    sender = str(payload.sender_email or settings.SMTP_SENDER).strip().lower()
    reply_to = str(payload.reply_to).strip().lower()
    if sender != settings.SMTP_SENDER.strip().lower():
        raise BadRequestException("Sender must match the configured and verified sender identity")

    base_query = (
        select(StudentProfile, User)
        .join(User, User.id == StudentProfile.user_id)
        .where(StudentProfile.institution_id == auth.institution_id, User.is_active.is_(True))
    )
    inclusion_reason: str = payload.audience_type
    excluded_count = duplicate_count = unresolved_count = 0
    missing_docs: dict[uuid.UUID, str] = {}
    if payload.audience_type == "current_eligible":
        base_query = base_query.join(
            EligibilityResult, EligibilityResult.student_profile_id == StudentProfile.id
        ).where(
            EligibilityResult.evaluation_run_id == drive.published_evaluation_run_id,
            EligibilityResult.outcome == "eligible",
        )
        total = await session.scalar(
            select(func.count())
            .select_from(EligibilityResult)
            .where(EligibilityResult.evaluation_run_id == drive.published_evaluation_run_id)
        )
        eligible = await session.scalar(
            select(func.count())
            .select_from(EligibilityResult)
            .where(
                EligibilityResult.evaluation_run_id == drive.published_evaluation_run_id,
                EligibilityResult.outcome == "eligible",
            )
        )
        excluded_count = int(total or 0) - int(eligible or 0)
        inclusion_reason = "Current published evaluation outcome is eligible"
    elif payload.audience_type == "submitted_registrants":
        base_query = base_query.join(
            Registration, Registration.student_profile_id == StudentProfile.id
        ).where(Registration.drive_id == drive.id, Registration.state == "submitted")
        inclusion_reason = "Registration is currently submitted"
    elif payload.audience_type == "explicit_recipients":
        base_query = base_query.where(StudentProfile.id.in_(payload.explicit_student_ids))
        inclusion_reason = "Explicitly reviewed recipient"
    elif payload.audience_type == "required_document_findings":
        eligible_rows = (
            await session.execute(
                base_query.join(
                    EligibilityResult, EligibilityResult.student_profile_id == StudentProfile.id
                ).where(
                    EligibilityResult.evaluation_run_id == drive.published_evaluation_run_id,
                    EligibilityResult.outcome == "eligible",
                )
            )
        ).all()
        selected_ids: list[uuid.UUID] = []
        for profile, _user in eligible_rows:
            readiness = await compute_readiness(
                session,
                institution_id=auth.institution_id,
                drive=drive,
                student_profile_id=profile.id,
            )
            if readiness["status"] != "ready":
                selected_ids.append(profile.id)
                labels = [
                    row["display_label"]
                    for row in readiness["requirements"]
                    if row["status"] != "ready"
                ]
                missing_docs[profile.id] = ", ".join(labels) or "required documents"
        excluded_count = len(eligible_rows) - len(selected_ids)
        base_query = base_query.where(StudentProfile.id.in_(selected_ids))
        inclusion_reason = "Current required-document readiness has findings"

    rows = (await session.execute(base_query.order_by(StudentProfile.student_identifier))).all()
    if payload.audience_type == "explicit_recipients" and len(rows) != len(
        set(payload.explicit_student_ids)
    ):
        raise BadRequestException(
            "One or more explicit recipients are unavailable in this institution"
        )

    next_revision = (
        int(
            await session.scalar(
                select(func.coalesce(func.max(CommunicationDraft.revision_number), 0)).where(
                    CommunicationDraft.drive_id == drive.id,
                    CommunicationDraft.communication_kind == payload.communication_kind,
                )
            )
            or 0
        )
        + 1
    )
    content_hash = canonical_hash(
        {
            "template_version": TEMPLATE_VERSION,
            "subject": subject,
            "body": body,
            "sender": sender,
            "reply_to": reply_to,
        }
    )
    draft = CommunicationDraft(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        revision_number=next_revision,
        communication_kind=payload.communication_kind,
        audience_type=payload.audience_type,
        template_version=TEMPLATE_VERSION,
        subject_template=subject,
        body_template=body,
        sender_email=sender,
        reply_to=reply_to,
        state="draft",
        content_hash=content_hash,
        created_by_membership_id=auth.membership_id,
    )
    session.add(draft)
    await session.flush()

    deduped: dict[str, tuple[StudentProfile, User]] = {}
    for profile, user in rows:
        normalized = user.email.strip().lower()
        if not normalized or "@" not in normalized:
            unresolved_count += 1
            continue
        if normalized in deduped:
            duplicate_count += 1
            continue
        deduped[normalized] = (profile, user)

    audience_descriptor = [
        {
            "student_profile_id": str(profile.id),
            "email": email,
            "contact_revision": contact_revision(user),
        }
        for email, (profile, user) in sorted(deduped.items())
    ]
    audience_hash = canonical_hash(audience_descriptor)
    snapshot = AudienceSnapshot(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        communication_draft_id=draft.id,
        audience_type=payload.audience_type,
        query_spec={
            "type": payload.audience_type,
            "published_evaluation_run_id": str(drive.published_evaluation_run_id),
            "explicit_student_ids": [str(item) for item in payload.explicit_student_ids],
        },
        included_count=len(deduped),
        excluded_count=excluded_count,
        duplicate_count=duplicate_count,
        unresolved_count=unresolved_count,
        exclusion_summary={
            "not_selected": excluded_count,
            "duplicate_address": duplicate_count,
            "unresolved_address": unresolved_count,
        },
        canonical_hash=audience_hash,
    )
    session.add(snapshot)
    await session.flush()

    recipients: list[AudienceRecipient] = []
    try:
        deadline = revision.registration_end_at.astimezone(
            ZoneInfo(institution.timezone)
        ).isoformat()
    except ZoneInfoNotFoundError as exc:
        raise ConflictException("Institution timezone configuration is invalid") from exc
    for email, (profile, user) in sorted(deduped.items()):
        merge_data = {
            "student_name": user.full_name,
            "company_name": company.name,
            "role_title": revision.role_title,
            "registration_link": f"{settings.PUBLIC_WEB_URL}/student/drives?drive={drive.id}",
            "registration_deadline": deadline,
            "timezone": institution.timezone,
            "required_documents": missing_docs.get(profile.id, "required documents"),
            "reply_to": reply_to,
        }
        rendered_subject = render_template(subject, merge_data)
        rendered_body = render_template(body, merge_data)
        recipient = AudienceRecipient(
            institution_id=auth.institution_id,
            audience_snapshot_id=snapshot.id,
            student_profile_id=profile.id,
            user_id=user.id,
            email=user.email,
            normalized_email=email,
            display_name=user.full_name,
            inclusion_reason=inclusion_reason,
            contact_revision=contact_revision(user),
            merge_data=merge_data,
            rendered_subject=rendered_subject,
            rendered_body=rendered_body,
            rendered_hash=canonical_hash({"subject": rendered_subject, "body": rendered_body}),
        )
        session.add(recipient)
        recipients.append(recipient)
    await session.flush()
    if not recipients:
        raise BadRequestException("The selected audience contains no deliverable recipients")
    return draft, snapshot, recipients


def proposal_envelope(
    institution_id: uuid.UUID,
    draft: CommunicationDraft,
    snapshot: AudienceSnapshot,
    dependencies: dict[str, Any],
    execution_expires_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "institution_id": str(institution_id),
        "action_type": "send_communication",
        "target_id": str(draft.id),
        "payload": {
            "communication_draft_id": str(draft.id),
            "audience_snapshot_id": str(snapshot.id),
            "content_hash": draft.content_hash,
            "audience_hash": snapshot.canonical_hash,
            "sender": draft.sender_email,
            "reply_to": draft.reply_to,
            "channel": draft.channel,
            "recipient_count": snapshot.included_count,
        },
        "dependencies": dependencies,
        "execution_expires_at": execution_expires_at.astimezone(UTC).isoformat(),
    }


async def create_communication_proposal(
    session: AsyncSession,
    auth: AuthContext,
    drive: Drive,
    draft: CommunicationDraft,
    snapshot: AudienceSnapshot,
    execution_expires_at: datetime,
) -> ActionProposal:
    """Persist the exact generic proposal shared by HTTP and workflow orchestration."""
    evaluation = await session.get(EvaluationRun, drive.published_evaluation_run_id)
    if not evaluation or evaluation.status != "completed" or evaluation.is_stale:
        raise ConflictException("Communication review requires a current completed evaluation")
    dependencies = {
        "drive_concurrency_revision": drive.concurrency_revision,
        "published_drive_revision_id": str(drive.published_drive_revision_id),
        "published_evaluation_run_id": str(drive.published_evaluation_run_id),
        "evaluation_run_fingerprint": evaluation.run_fingerprint,
        "policy_id": str(evaluation.policy_id),
        "content_hash": draft.content_hash,
        "audience_hash": snapshot.canonical_hash,
        "sender_connection_revision": sender_connection_revision(),
    }
    envelope = proposal_envelope(
        auth.institution_id, draft, snapshot, dependencies, execution_expires_at
    )
    proposal = ActionProposal(
        institution_id=auth.institution_id,
        drive_id=drive.id,
        action_type="send_communication",
        target_type="communication_draft",
        target_id=draft.id,
        revision_number=draft.revision_number,
        schema_version=1,
        payload=envelope["payload"],
        dependencies=dependencies,
        canonical_hash=canonical_hash(envelope),
        state="pending_approval",
        requested_by_membership_id=auth.membership_id,
        expires_at=execution_expires_at,
        execution_expires_at=execution_expires_at,
        execution_bounds={"max_recipients": snapshot.included_count, "channel": "email"},
        sender_connection_revision=dependencies["sender_connection_revision"],
    )
    session.add(proposal)
    draft.state = "in_review"
    await session.flush()
    return proposal
