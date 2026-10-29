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
from placementos.models.intelligence import (
    ActionProposal,
    ApprovalDecision,
    ClarificationTask,
    EligibilityPolicyVersion,
    JDInterpretationRevision,
    JDReviewCorrection,
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
    "ActionProposal",
    "ApprovalDecision",
    "AuditLog",
    "Company",
    "ClarificationTask",
    "DomainJob",
    "Drive",
    "DriveAssignment",
    "DriveRevision",
    "EligibilityPolicyVersion",
    "Institution",
    "JDInterpretationRevision",
    "JDReviewCorrection",
    "Membership",
    "SourceArtifact",
    "StudentCorrectionProposal",
    "StudentProfile",
    "TextExtraction",
    "UploadSession",
    "User",
]
