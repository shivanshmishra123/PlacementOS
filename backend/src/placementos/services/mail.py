"""Controlled email provider boundary with honest outcome classification."""

from __future__ import annotations

import smtplib
import uuid
from dataclasses import dataclass
from email.message import EmailMessage

from placementos.core.config import settings


@dataclass(frozen=True)
class FrozenEmail:
    operation_key: str
    sender: str
    reply_to: str
    recipient: str
    recipient_name: str
    subject: str
    body: str


@dataclass(frozen=True)
class ProviderOutcome:
    status: str
    provider_message_id: str | None = None
    error_code: str | None = None
    error_detail: str | None = None
    evidence: dict[str, str] | None = None


class EmailAdapter:
    adapter_id = "abstract"

    def send(self, message: FrozenEmail) -> ProviderOutcome:
        raise NotImplementedError


class DisabledEmailAdapter(EmailAdapter):
    adapter_id = "disabled"

    def send(self, message: FrozenEmail) -> ProviderOutcome:
        return ProviderOutcome(
            status="failed",
            error_code="EMAIL_ADAPTER_DISABLED",
            error_detail="Email transport is disabled",
        )


class SMTPEmailAdapter(EmailAdapter):
    """SMTP sink/transport. SMTP acceptance is not represented as final delivery."""

    adapter_id = "mailpit-smtp-v1" if settings.EMAIL_ADAPTER_MODE == "mailpit" else "smtp-v1"

    def send(self, message: FrozenEmail) -> ProviderOutcome:
        email = EmailMessage()
        email["From"] = message.sender
        email["To"] = message.recipient
        email["Reply-To"] = message.reply_to
        email["Subject"] = message.subject
        provider_message_id = (
            f"<{uuid.uuid5(uuid.NAMESPACE_URL, message.operation_key)}@placementos.local>"
        )
        email["Message-ID"] = provider_message_id
        email["X-PlacementOS-Operation-Key"] = message.operation_key
        email.set_content(message.body)
        try:
            with smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.EMAIL_SEND_TIMEOUT_SECONDS,
            ) as smtp:
                if settings.SMTP_TLS:
                    smtp.starttls()
                if settings.SMTP_USER:
                    smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                smtp.send_message(email)
            return ProviderOutcome(
                status="provider_accepted",
                provider_message_id=provider_message_id,
                evidence={"adapter": self.adapter_id, "receipt_semantics": "smtp_acceptance_only"},
            )
        except smtplib.SMTPRecipientsRefused as exc:
            return ProviderOutcome(
                status="failed",
                error_code="RECIPIENT_REJECTED",
                error_detail=str(exc)[:500],
            )
        except (TimeoutError, smtplib.SMTPServerDisconnected) as exc:
            return ProviderOutcome(
                status="unknown",
                error_code="PROVIDER_OUTCOME_UNKNOWN",
                error_detail=str(exc)[:500],
            )
        except (ConnectionRefusedError, OSError, smtplib.SMTPException) as exc:
            return ProviderOutcome(
                status="retryable_failure",
                error_code="PROVIDER_UNAVAILABLE",
                error_detail=str(exc)[:500],
            )


def get_email_adapter() -> EmailAdapter:
    if settings.EMAIL_ADAPTER_MODE == "disabled":
        return DisabledEmailAdapter()
    return SMTPEmailAdapter()
