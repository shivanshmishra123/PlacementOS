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
            "student:read",
            "student:import",
            "eligibility:run",
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
        "capabilities": ["member:manage", "config:manage", "audit:view"],
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
