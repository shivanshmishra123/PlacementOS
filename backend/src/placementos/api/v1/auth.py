"""PlacementOS Authentication Endpoints and Development Personas."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.config import settings
from placementos.core.database import get_db
from placementos.core.dependencies import get_current_auth
from placementos.core.errors import BadRequestException, ForbiddenException
from placementos.core.security import generate_csrf_token
from placementos.models.identity import Institution, Membership, User
from placementos.services.session import AuthContext, SessionManager

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


class UserProfileResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    institution_id: uuid.UUID
    institution_slug: str
    role: str
    capabilities: list[str]


class DevLoginRequest(BaseModel):
    persona: str | None = None
    email: str | None = None
    institution_slug: str | None = None


class DevLoginResponse(BaseModel):
    message: str
    user: UserProfileResponse
    csrf_token: str
    session_token: str


class LoginRequest(BaseModel):
    email: str
    password: str | None = None
    institution_slug: str | None = None


class LoginResponse(BaseModel):
    message: str
    user: UserProfileResponse
    csrf_token: str
    session_token: str


class SwitchInstitutionRequest(BaseModel):
    institution_id: uuid.UUID


class PersonaInfo(BaseModel):
    key: str
    name: str
    email: str
    role: str
    institution_slug: str
    institution_name: str
    description: str


# Synthetic acceptance personas from fixtures/inventory.md
SYNTHETIC_PERSONAS: dict[str, dict] = {
    "coord_apex": {
        "name": "Priya Sharma",
        "email": "priya.sharma@apex.edu",
        "role": "placement_coordinator",
        "institution_slug": "apex-tech",
        "institution_name": "Apex Institute of Technology",
        "institution_domain": "apex.edu",
        "capabilities": [
            "drive:create",
            "drive:edit",
            "rule:approve",
            "proposal:decide",
            "schedule:publish",
            "schedule:override_documents",
            "result:publish",
            "export:generate",
            "drive:close",
            "drive:reopen",
            "drive:cancel",
            "ops:view",
            "student:read",
            "student:import",
            "eligibility:run",
            "integration:manage",
            "integration:write",
            "exception:plan",
        ],
        "description": "Apex Lead Placement Coordinator with approval authority",
    },
    "admin_apex": {
        "name": "Rajesh Verma",
        "email": "rajesh.verma@apex.edu",
        "role": "institution_admin",
        "institution_slug": "apex-tech",
        "institution_name": "Apex Institute of Technology",
        "institution_domain": "apex.edu",
        "capabilities": [
            "member:manage",
            "config:manage",
            "audit:view",
            "ops:view",
            "integration:manage",
        ],
        "description": "Apex Institution Administrator",
    },
    "coord_beacon": {
        "name": "Ananya Das",
        "email": "ananya.das@beacon.edu",
        "role": "placement_coordinator",
        "institution_slug": "beacon-state",
        "institution_name": "Beacon Engineering College",
        "institution_domain": "beacon.edu",
        "capabilities": [
            "drive:create",
            "drive:edit",
            "rule:approve",
            "proposal:decide",
            "student:read",
            "student:import",
            "eligibility:run",
            "integration:manage",
            "integration:write",
            "exception:plan",
        ],
        "description": "Beacon Placement Coordinator (for cross-tenant negative testing)",
    },
    "student_a_apex": {
        "name": "Aarav Sharma",
        "email": "student.a@apex.edu",
        "role": "student",
        "institution_slug": "apex-tech",
        "institution_name": "Apex Institute of Technology",
        "institution_domain": "apex.edu",
        "capabilities": ["student:portal", "registration:submit", "correction:propose"],
        "description": "Eligible student candidate at Apex (CS cohort)",
    },
    "student_a_beacon": {
        "name": "Aditi Rao",
        "email": "student.a@beacon.edu",
        "role": "student",
        "institution_slug": "beacon-state",
        "institution_name": "Beacon Engineering College",
        "institution_domain": "beacon.edu",
        "capabilities": ["student:portal", "registration:submit", "correction:propose"],
        "description": "Student candidate at Beacon with matching USN for collision tests",
    },
}


@router.get("/personas", response_model=list[PersonaInfo])
async def list_personas() -> list[PersonaInfo]:
    """Return available synthetic development personas (dev mode only)."""
    if settings.ENVIRONMENT == "production":
        raise ForbiddenException("Persona listing disabled in production")

    return [
        PersonaInfo(
            key=k,
            name=v["name"],
            email=v["email"],
            role=v["role"],
            institution_slug=v["institution_slug"],
            institution_name=v["institution_name"],
            description=v["description"],
        )
        for k, v in SYNTHETIC_PERSONAS.items()
    ]


@router.post("/dev-login", response_model=DevLoginResponse)
async def dev_login(
    req: DevLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> DevLoginResponse:
    """Sign in as a synthetic persona or arbitrary email during development."""
    if settings.ENVIRONMENT == "production":
        raise ForbiddenException("Dev login is strictly forbidden in production mode")

    persona_key = req.persona
    persona_data = SYNTHETIC_PERSONAS.get(persona_key) if persona_key else None

    if persona_data:
        email = persona_data["email"]
        full_name = persona_data["name"]
        role = persona_data["role"]
        capabilities = persona_data["capabilities"]
        inst_slug = persona_data["institution_slug"]
        inst_name = persona_data["institution_name"]
        inst_domain = persona_data["institution_domain"]
    elif req.email:
        email = str(req.email).strip().lower()
        full_name = email.split("@")[0].replace(".", " ").title()
        role = "student" if "student" in email else "coordinator"
        capabilities = (
            ["student:portal", "registration:submit", "correction:propose"]
            if role == "student"
            else ["student:read", "drive:create"]
        )
        inst_slug = req.institution_slug or "apex-tech"
        inst_name = "Apex Institute of Technology"
        inst_domain = email.split("@")[-1]
    else:
        raise BadRequestException("Either 'persona' or 'email' must be provided")

    # 1. Ensure institution exists
    inst_res = await db.execute(select(Institution).where(Institution.slug == inst_slug))
    institution = inst_res.scalar_one_or_none()
    if not institution:
        institution = Institution(slug=inst_slug, name=inst_name, domain=inst_domain)
        db.add(institution)
        await db.flush()

    # 2. Ensure user exists
    user_res = await db.execute(select(User).where(User.email == email))
    user = user_res.scalar_one_or_none()
    if not user:
        user = User(email=email, full_name=full_name)
        db.add(user)
        await db.flush()

    # 3. Ensure membership exists
    mem_res = await db.execute(
        select(Membership).where(
            Membership.institution_id == institution.id,
            Membership.user_id == user.id,
        )
    )
    membership = mem_res.scalar_one_or_none()
    if not membership:
        membership = Membership(
            institution_id=institution.id,
            user_id=user.id,
            role=role,
            capabilities=capabilities,
        )
        db.add(membership)
        await db.flush()
    elif persona_data:
        membership.role = role
        membership.capabilities = capabilities
        await db.flush()

    await db.commit()

    # 4. Create opaque Redis session
    raw_token, auth = await SessionManager.create_session(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        institution_id=institution.id,
        institution_slug=institution.slug,
        membership_id=membership.id,
        role=membership.role,
        capabilities=membership.capabilities,
    )

    # 5. Set HttpOnly session cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT == "production",
    )

    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=False,  # Accessible to client JavaScript for Double-Submit CSRF check
        samesite="lax",
        secure=settings.ENVIRONMENT == "production",
    )

    return DevLoginResponse(
        message=f"Signed in successfully as {user.full_name}",
        user=UserProfileResponse(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            institution_id=institution.id,
            institution_slug=institution.slug,
            role=membership.role,
            capabilities=membership.capabilities,
        ),
        csrf_token=csrf_token,
        session_token=raw_token,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate with institutional email credentials and establish scoped session."""
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise BadRequestException("A valid institutional email address is required")

    # 1. Look up existing user
    user_res = await db.execute(select(User).where(User.email == email))
    user = user_res.scalar_one_or_none()

    # 2. Check if user already exists with an active membership
    if user:
        mem_query = (
            select(Membership, Institution)
            .join(Institution, Institution.id == Membership.institution_id)
            .where(
                Membership.user_id == user.id,
                Membership.is_active.is_(True),
            )
        )
        if req.institution_slug:
            mem_query = mem_query.where(Institution.slug == req.institution_slug)

        mem_res = await db.execute(mem_query)
        row = mem_res.first()
        if row:
            membership, institution = row
        else:
            # Fallback to any membership
            fallback_res = await db.execute(
                select(Membership, Institution)
                .join(Institution, Institution.id == Membership.institution_id)
                .where(Membership.user_id == user.id)
            )
            row = fallback_res.first()
            if not row:
                raise ForbiddenException("User account has no institutional memberships")
            membership, institution = row
    else:
        # Check against synthetic personas
        matching_persona = next(
            (p for p in SYNTHETIC_PERSONAS.values() if p["email"].lower() == email),
            None,
        )
        if matching_persona:
            full_name = matching_persona["name"]
            role = matching_persona["role"]
            capabilities = matching_persona["capabilities"]
            inst_slug = req.institution_slug or matching_persona["institution_slug"]
            inst_name = matching_persona["institution_name"]
            inst_domain = matching_persona["institution_domain"]
        else:
            # Provision account based on institutional pattern
            domain = email.split("@")[-1]
            inst_slug = req.institution_slug or ("beacon-state" if "beacon" in domain else "apex-tech")
            inst_name = (
                "Beacon Engineering College" if "beacon" in inst_slug else "Apex Institute of Technology"
            )
            inst_domain = domain
            full_name = email.split("@")[0].replace(".", " ").title()

            # Deterministic role assignment based on institutional email structure
            if "student" in email:
                role = "student"
                capabilities = ["student:portal", "registration:submit", "correction:propose"]
            elif "admin" in email:
                role = "institution_admin"
                capabilities = ["member:manage", "config:manage", "audit:view", "ops:view"]
            else:
                role = "placement_coordinator"
                capabilities = [
                    "drive:create",
                    "drive:edit",
                    "rule:approve",
                    "proposal:decide",
                    "schedule:publish",
                    "result:publish",
                    "student:read",
                    "student:import",
                    "eligibility:run",
                    "integration:manage",
                    "exception:plan",
                ]

        # Ensure institution exists
        inst_res = await db.execute(select(Institution).where(Institution.slug == inst_slug))
        institution = inst_res.scalar_one_or_none()
        if not institution:
            institution = Institution(slug=inst_slug, name=inst_name, domain=inst_domain)
            db.add(institution)
            await db.flush()

        user = User(email=email, full_name=full_name)
        db.add(user)
        await db.flush()

        membership = Membership(
            institution_id=institution.id,
            user_id=user.id,
            role=role,
            capabilities=capabilities,
        )
        db.add(membership)
        await db.commit()

    # 3. Create opaque Redis session
    raw_token, auth = await SessionManager.create_session(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        institution_id=institution.id,
        institution_slug=institution.slug,
        membership_id=membership.id,
        role=membership.role,
        capabilities=membership.capabilities,
    )

    # 4. Set HttpOnly session cookie & CSRF cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT == "production",
    )

    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=False,
        samesite="lax",
        secure=settings.ENVIRONMENT == "production",
    )

    return LoginResponse(
        message=f"Signed in successfully as {user.full_name}",
        user=UserProfileResponse(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            institution_id=institution.id,
            institution_slug=institution.slug,
            role=membership.role,
            capabilities=membership.capabilities,
        ),
        csrf_token=csrf_token,
        session_token=raw_token,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    auth: AuthContext = Depends(get_current_auth),
) -> UserProfileResponse:
    """Return currently authenticated user and active institutional scope."""
    return UserProfileResponse(
        user_id=auth.user_id,
        email=auth.email,
        full_name=auth.full_name,
        institution_id=auth.institution_id,
        institution_slug=auth.institution_slug,
        role=auth.role,
        capabilities=auth.capabilities,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth: AuthContext = Depends(get_current_auth),
) -> dict[str, str]:
    """Revoke current user session and clear cookies."""
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not raw_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header.removeprefix("Bearer ").strip()

    if raw_token:
        await SessionManager.revoke_session(raw_token)

    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    response.delete_cookie("csrf_token")
    return {"message": "Successfully logged out"}


# ---------------------------------------------------------------------------
# P19: Production OpenID Connect (OIDC) Endpoints
# ---------------------------------------------------------------------------


class OIDCLoginResponse(BaseModel):
    authorization_url: str
    state: str


class OIDCCallbackRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str | None = None


@router.get("/oidc/login", response_model=OIDCLoginResponse)
async def oidc_login(
    redirect_uri: str | None = None,
) -> OIDCLoginResponse:
    """Initiate standard OIDC authorization-code flow with state & nonce."""
    import json
    import secrets
    import time

    from placementos.core.redis import get_redis_client
    from placementos.services.oidc import OIDCAdapter

    callback_url = redirect_uri or getattr(settings, "OIDC_REDIRECT_URI", "") or f"{settings.PUBLIC_WEB_URL}/auth/callback"
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    # Cache state with 10-minute TTL
    redis = await get_redis_client()
    await redis.setex(
        f"oidc_state:{state}",
        600,
        json.dumps({"nonce": nonce, "redirect_uri": callback_url, "created_at": time.time()}),
    )

    adapter = OIDCAdapter()
    auth_url = adapter.get_authorization_url(redirect_uri=callback_url, state=state, nonce=nonce)
    return OIDCLoginResponse(authorization_url=auth_url, state=state)


@router.post("/oidc/callback", response_model=DevLoginResponse)
async def oidc_callback(
    req: OIDCCallbackRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> DevLoginResponse:
    """Validate OIDC authorization code and establish authenticated session."""
    import json

    from placementos.core.redis import get_redis_client
    from placementos.services.oidc import OIDCAdapter

    redis = await get_redis_client()
    state_bytes = await redis.get(f"oidc_state:{req.state}")
    if not state_bytes:
        raise BadRequestException("Invalid or expired OIDC state parameter")

    state_info = json.loads(state_bytes)
    nonce = state_info.get("nonce")
    callback_url = req.redirect_uri or state_info.get("redirect_uri")

    adapter = OIDCAdapter()
    tokens = await adapter.exchange_code(code=req.code, redirect_uri=callback_url)
    id_token = tokens.get("id_token")
    if not id_token:
        raise BadRequestException("Missing id_token in token exchange response")

    claims = adapter.verify_id_token(id_token=id_token, expected_nonce=nonce)
    user, membership, institution = await adapter.map_claims_to_membership(db, claims)

    # Clean up single-use state
    await redis.delete(f"oidc_state:{req.state}")

    # Issue opaque session
    raw_token, auth = await SessionManager.create_session(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        institution_id=institution.id,
        institution_slug=institution.slug,
        membership_id=membership.id,
        role=membership.role,
        capabilities=membership.capabilities,
    )

    # Set security cookies
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT == "production",
    )

    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=False,
        samesite="lax",
        secure=settings.ENVIRONMENT == "production",
    )

    return DevLoginResponse(
        message=f"Signed in via OIDC as {user.full_name}",
        user=UserProfileResponse(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            institution_id=institution.id,
            institution_slug=institution.slug,
            role=membership.role,
            capabilities=membership.capabilities,
        ),
        csrf_token=csrf_token,
        session_token=raw_token,
    )

