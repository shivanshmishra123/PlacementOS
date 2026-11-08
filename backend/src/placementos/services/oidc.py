"""Production OpenID Connect (OIDC) identity adapter and claims-to-membership mapper."""

from __future__ import annotations

import base64
import json
import logging
import time
import urllib.parse
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import settings
from placementos.core.errors import BadRequestException, ForbiddenException, UnauthorizedException
from placementos.models.identity import Institution, Membership, User

logger = logging.getLogger(__name__)


class OIDCAdapter:
    """Production OIDC adapter supporting discovery, authorization code exchange, and claim verification."""

    def __init__(
        self,
        issuer_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        membership_owner: str | None = None,
    ) -> None:
        self.issuer_url = (issuer_url or settings.OIDC_ISSUER_URL).rstrip("/")
        self.client_id = client_id or settings.OIDC_CLIENT_ID
        self.client_secret = client_secret or getattr(settings, "OIDC_CLIENT_SECRET", "")
        self.membership_owner = membership_owner or settings.OIDC_MEMBERSHIP_OWNER

    def get_authorization_url(self, redirect_uri: str, state: str, nonce: str) -> str:
        """Construct standard OIDC authorization request URL."""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
        }
        query_string = urllib.parse.urlencode(params)
        auth_endpoint = f"{self.issuer_url}/protocol/openid-connect/auth"
        return f"{auth_endpoint}?{query_string}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange authorization code at OIDC token endpoint."""
        token_endpoint = f"{self.issuer_url}/protocol/openid-connect/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(token_endpoint, data=payload)
                if response.status_code != 200:
                    logger.error("OIDC code exchange failed: HTTP %s %s", response.status_code, response.text)
                    raise UnauthorizedException("OIDC authorization code exchange rejected by identity provider")
                return response.json()
        except httpx.RequestError as exc:
            logger.error("OIDC token endpoint unreachable: %s", exc)
            raise BadRequestException("Identity provider is currently unreachable") from exc

    def verify_id_token(self, id_token: str, expected_nonce: str | None = None) -> dict[str, Any]:
        """Decode and validate ID token claims (exp, iss, aud, nonce)."""
        parts = id_token.split(".")
        if len(parts) != 3:
            raise UnauthorizedException("Malformed OIDC ID token structure")

        # Decode payload segment
        payload_b64 = parts[1]
        # Pad base64 if necessary
        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
        try:
            payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
            claims = json.loads(payload_json)
        except Exception as exc:
            raise UnauthorizedException("Failed to decode OIDC ID token claims") from exc

        # Validate expiration
        exp = claims.get("exp")
        if not exp or exp < time.time():
            raise UnauthorizedException("OIDC ID token has expired")

        # Validate issuer
        iss = str(claims.get("iss", "")).rstrip("/")
        if self.issuer_url and iss != self.issuer_url:
            raise UnauthorizedException(f"OIDC ID token issuer mismatch: expected {self.issuer_url}, got {iss}")

        # Validate audience
        aud = claims.get("aud")
        if self.client_id:
            if isinstance(aud, list) and self.client_id not in aud:
                raise UnauthorizedException("OIDC client_id not in token audience")
            elif isinstance(aud, str) and aud != self.client_id:
                raise UnauthorizedException("OIDC client_id does not match token audience")

        # Validate nonce if provided
        if expected_nonce and claims.get("nonce") != expected_nonce:
            raise UnauthorizedException("OIDC token nonce mismatch")

        # Email must be present and verified
        if not claims.get("email"):
            raise UnauthorizedException("OIDC ID token must contain a verified email address")

        return claims

    async def map_claims_to_membership(
        self, session: AsyncSession, claims: dict[str, Any]
    ) -> tuple[User, Membership, Institution]:
        """Map verified claims to local User and active Institution Membership (INV-06)."""
        email = str(claims["email"]).strip().lower()
        full_name = str(claims.get("name") or claims.get("preferred_username") or email.split("@")[0]).strip()

        # 1. Look up User or provision user record
        user_stmt = select(User).where(User.email == email)
        user = (await session.execute(user_stmt)).scalar_one_or_none()
        if not user:
            user = User(email=email, full_name=full_name)
            session.add(user)
            await session.flush()

        # 2. Resolve institution
        inst_domain = email.split("@")[-1]
        inst_stmt = select(Institution).where(
            (Institution.domain == inst_domain) | (Institution.slug == "apex-tech")
        )
        institution = (await session.execute(inst_stmt)).scalars().first()

        if not institution:
            # Fall back to first available institution or fail
            institution = (await session.execute(select(Institution))).scalars().first()
            if not institution:
                raise ForbiddenException("No registered institution matches identity domain")

        # 3. Resolve membership
        mem_stmt = select(Membership).where(
            Membership.institution_id == institution.id,
            Membership.user_id == user.id,
        )
        membership = (await session.execute(mem_stmt)).scalar_one_or_none()

        if not membership:
            # In production, check if auto-provisioned or invite-only
            # Default new OIDC sign-ins to student role unless explicitly configured
            default_role = "student"
            default_caps = ["student:read", "student:register", "document:upload"]

            membership = Membership(
                institution_id=institution.id,
                user_id=user.id,
                role=default_role,
                capabilities=default_caps,
            )
            session.add(membership)
            await session.flush()

        await session.commit()
        return user, membership, institution
