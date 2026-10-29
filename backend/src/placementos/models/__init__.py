"""PlacementOS Domain Models Package."""

from placementos.models.academic import (
    AcademicRecordRevision,
    StudentCorrectionProposal,
)
from placementos.models.identity import (
    AuditLog,
    DriveAssignment,
    Institution,
    Membership,
    StudentProfile,
    User,
)
from placementos.models.recruitment import (
    Company,
    Drive,
    DriveRevision,
)
from placementos.models.storage import (
    DomainJob,
    SourceArtifact,
    TextExtraction,
    UploadSession,
)

__all__ = [
    "AcademicRecordRevision",
    "AuditLog",
    "Company",
    "DomainJob",
    "Drive",
    "DriveAssignment",
    "DriveRevision",
    "Institution",
    "Membership",
    "SourceArtifact",
    "StudentCorrectionProposal",
    "StudentProfile",
    "TextExtraction",
    "UploadSession",
    "User",
]
