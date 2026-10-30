"""PlacementOS Domain Models Package."""

from placementos.models.academic import (
    AcademicRecordRevision,
    StudentCorrectionProposal,
)
from placementos.models.communications import (
    AudienceRecipient,
    AudienceSnapshot,
    CommunicationDraft,
    DispatchAttempt,
    DispatchBatch,
    DispatchOperation,
    OutboxEvent,
)
from placementos.models.eligibility import (
    EligibilityResult,
    EligibilityReviewRequest,
    EvaluationCohortMember,
    EvaluationRun,
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
from placementos.models.participation import (
    DocumentRevision,
    DocumentValidationRun,
    DriveDocumentRequirement,
    Registration,
    RegistrationEvent,
    StudentDocument,
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
from placementos.models.workflow import ExceptionCase, WorkflowCommand, WorkflowEvent, WorkflowRun

__all__ = [
    "AcademicRecordRevision",
    "ActionProposal",
    "ApprovalDecision",
    "AuditLog",
    "AudienceRecipient",
    "AudienceSnapshot",
    "Company",
    "ClarificationTask",
    "CommunicationDraft",
    "DomainJob",
    "DocumentRevision",
    "DocumentValidationRun",
    "DispatchAttempt",
    "DispatchBatch",
    "DispatchOperation",
    "Drive",
    "DriveAssignment",
    "DriveRevision",
    "DriveDocumentRequirement",
    "EligibilityPolicyVersion",
    "EligibilityResult",
    "EligibilityReviewRequest",
    "ExceptionCase",
    "EvaluationCohortMember",
    "EvaluationRun",
    "Institution",
    "JDInterpretationRevision",
    "JDReviewCorrection",
    "Membership",
    "OutboxEvent",
    "Registration",
    "RegistrationEvent",
    "SourceArtifact",
    "StudentCorrectionProposal",
    "StudentDocument",
    "StudentProfile",
    "TextExtraction",
    "UploadSession",
    "User",
    "WorkflowCommand",
    "WorkflowEvent",
    "WorkflowRun",
]
