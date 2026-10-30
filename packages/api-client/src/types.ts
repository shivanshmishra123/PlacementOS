/**
 * PlacementOS Typed API Client Contracts
 * Generated from backend OpenAPI schema.
 */

export interface ErrorDetail {
  code: string;
  message: string;
  correlation_id?: string | null;
  details?: Record<string, unknown>;
}

export interface ErrorResponse {
  error: ErrorDetail;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  environment: string;
  version: string;
  correlation_id?: string | null;
}

export interface ReadinessResponse {
  status: "ready" | "not_ready";
  database: boolean;
  redis: boolean;
  correlation_id?: string | null;
}

export interface UserProfileResponse {
  user_id: string;
  email: string;
  full_name: string;
  institution_id: string;
  institution_slug: string;
  role: string;
  capabilities: string[];
}

export interface DevLoginRequest {
  persona?: string | null;
  email?: string | null;
  institution_slug?: string | null;
}

export interface DevLoginResponse {
  message: string;
  user: UserProfileResponse;
  csrf_token: string;
  session_token: string;
}

export interface PersonaInfo {
  key: string;
  name: string;
  email: string;
  role: string;
  institution_slug: string;
  institution_name: string;
  description: string;
}

export interface AcademicRevisionDTO {
  id: string;
  revision_number: number;
  source: string;
  source_reference?: string | null;
  is_verified: boolean;
  verified_at?: string | null;
  branch: string;
  cgpa: number;
  cgpa_scale: number;
  graduation_year: number;
  active_backlogs?: number | null;
  history_backlogs?: number | null;
  created_at: string;
}

export interface StudentListItemDTO {
  id: string;
  student_identifier: string;
  full_name: string;
  email: string;
  branch?: string | null;
  cgpa?: number | null;
  cgpa_scale?: number | null;
  graduation_year?: number | null;
  active_backlogs?: number | null;
  is_verified: boolean;
  created_at: string;
}

export interface StudentDetailDTO {
  id: string;
  student_identifier: string;
  full_name: string;
  email: string;
  institution_id: string;
  current_verified_revision?: AcademicRevisionDTO | null;
  revision_history: AcademicRevisionDTO[];
}

export interface CorrectionProposalDTO {
  id: string;
  student_profile_id: string;
  student_identifier: string;
  student_name: string;
  proposed_changes: Record<string, unknown>;
  justification: string;
  supporting_document_url?: string | null;
  status: "pending" | "approved" | "rejected";
  review_notes?: string | null;
  decided_at?: string | null;
  created_at: string;
}

// ==========================================
// Phase 3: Recruitment Drives & Companies
// ==========================================

export interface CompanyCreate {
  name: string;
  industry?: string | null;
  website?: string | null;
  description?: string | null;
}

export interface CompanyResponse {
  id: string;
  institution_id: string;
  name: string;
  industry?: string | null;
  website?: string | null;
  description?: string | null;
  created_at: string;
}

export interface DriveCreate {
  company_id: string;
  academic_year: string;
  title: string;
  description?: string | null;
}

export interface DriveUpdate {
  title?: string | null;
  description?: string | null;
  status?: string | null;
}

export interface DriveRevisionCreate {
  expected_revision_number: number;
  change_summary: string;
  proposed_changes?: Record<string, unknown>;
}

export interface DriveRevisionResponse {
  id: string;
  drive_id: string;
  revision_number: number;
  change_summary: string;
  proposed_changes: Record<string, unknown>;
  created_by_user_id?: string | null;
  created_at: string;
}

export interface SourceArtifactSummary {
  id: string;
  drive_id: string;
  source_type: string;
  original_filename?: string | null;
  status: string;
  hash_sha256: string;
  byte_size: number;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface DriveResponse {
  id: string;
  institution_id: string;
  company_id: string;
  company_name: string;
  academic_year: string;
  status: string;
  title: string;
  description?: string | null;
  current_revision_number: number;
  revisions: DriveRevisionResponse[];
  source_artifacts: SourceArtifactSummary[];
  created_at: string;
  updated_at: string;
}

export interface DriveListResponse {
  items: DriveResponse[];
  total: number;
  page: number;
  limit: number;
}

// ==========================================
// Phase 3: Storage, Intake & Extractions
// ==========================================

export interface UploadSessionCreate {
  drive_id: string;
  purpose?: string;
  original_filename: string;
  content_type: string;
  byte_size: number;
}

export interface UploadSessionResponse {
  id: string;
  drive_id: string;
  purpose: string;
  original_filename: string;
  storage_key: string;
  upload_url: string;
  expires_at: string;
  status: string;
  created_at: string;
}

export interface PastedSourceCreate {
  title?: string;
  raw_text: string;
}

export interface SourceArtifactResponse {
  id: string;
  institution_id: string;
  drive_id: string;
  source_type: string;
  original_filename?: string | null;
  file_extension?: string | null;
  hash_sha256: string;
  byte_size: number;
  status: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
  extracted_at?: string | null;
}

// ==========================================
// Phase 4: JD Intelligence & Policy Review
// ==========================================

export interface EvidenceLocator {
  field_path: string;
  locator_type: "page" | "paragraph" | "human_correction";
  page_number?: number | null;
  paragraph_index?: number | null;
  char_offset_start?: number | null;
  char_offset_end?: number | null;
  excerpt: string;
}

export interface ClarificationResponse {
  id: string;
  field_path: string;
  question: string;
  reason_code: string;
  blocking: boolean;
  status: string;
  resolution_value?: unknown;
  resolution_reason?: string | null;
}

export interface InterpretationResponse {
  id: string;
  drive_id: string;
  source_artifact_id: string;
  text_extraction_id: string;
  revision_number: number;
  schema_version: number;
  status: string;
  mode: string;
  adapter_id: string;
  candidate_facts: Record<string, unknown>;
  reviewed_facts: Record<string, unknown>;
  evidence: Record<string, unknown>[];
  validation_findings: Record<string, unknown>[];
  clarifications: ClarificationResponse[];
  created_at: string;
}

export interface PolicyResponse {
  id: string;
  drive_id: string;
  interpretation_id: string;
  version_number: number;
  schema_version: number;
  engine_contract: string;
  status: string;
  policy_payload: Record<string, unknown>;
  human_summary: string;
  canonical_hash: string;
  approved_proposal_id?: string | null;
  created_at: string;
}

export interface ProposalResponse {
  id: string;
  drive_id: string;
  action_type: string;
  target_type: string;
  target_id: string;
  revision_number: number;
  payload: Record<string, unknown>;
  dependencies: Record<string, unknown>;
  canonical_hash: string;
  state: string;
  expires_at?: string | null;
  created_at: string;
}

export interface DecisionResponse {
  id: string;
  proposal_id: string;
  decision: string;
  comment?: string | null;
  decided_at: string;
  proposal_state: string;
  policy_status: string;
}

// ==========================================
// Phase 5: Deterministic Eligibility
// ==========================================

export interface PredicateFindingResponse {
  predicate: string;
  outcome: "true" | "false" | "unknown";
  reason_code: string;
  expected: unknown;
  actual: unknown;
  evidence_status: string;
  explanation: string;
}

export interface EligibilityResultResponse {
  id: string;
  evaluation_run_id: string;
  student_profile_id: string;
  student_identifier: string;
  student_name: string;
  academic_revision_id?: string | null;
  outcome: "eligible" | "ineligible" | "needs_review";
  predicate_results: PredicateFindingResponse[];
  reason_codes: string[];
  student_explanation: string;
  input_fingerprint: string;
  created_at: string;
}

export interface EvaluationRunResponse {
  id: string;
  drive_id: string;
  policy_id: string;
  policy_version: number;
  policy_hash: string;
  engine_version: string;
  normalization_version: string;
  cohort_fingerprint: string;
  status: string;
  is_stale: boolean;
  stale_reason?: string | null;
  total_count: number;
  eligible_count: number;
  ineligible_count: number;
  needs_review_count: number;
  duration_ms?: number | null;
  error_code?: string | null;
  error_detail?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  results: EligibilityResultResponse[];
}

export interface StudentEligibilityResponse {
  result_id: string;
  evaluation_run_id: string;
  drive_id: string;
  drive_title: string;
  company_name: string;
  policy_version: number;
  outcome: "eligible" | "ineligible" | "needs_review";
  predicate_results: PredicateFindingResponse[];
  reason_codes: string[];
  student_explanation: string;
  is_stale: boolean;
  stale_reason?: string | null;
  evaluated_at: string;
}

export interface EligibilityReviewRequestResponse {
  id: string;
  drive_id: string;
  eligibility_result_id: string;
  student_profile_id: string;
  student_identifier: string;
  student_name: string;
  reason: string;
  status: string;
  created_at: string;
}

export interface TextLocator {
  locator_type: "page" | "paragraph";
  page_number?: number | null;
  paragraph_index: number;
  char_offset_start: number;
  char_offset_end: number;
  preview: string;
}

export interface TextExtractionResponse {
  id: string;
  source_artifact_id: string;
  institution_id: string;
  extracted_text: string;
  char_count: number;
  locators: TextLocator[];
  page_count?: number | null;
  paragraph_count: number;
  parser_version: string;
  is_empty_or_scanned: boolean;
  created_at: string;
}

export interface DownloadUrlResponse {
  download_url: string;
  expires_in: number;
  filename?: string | null;
}

export interface DomainJobResponse {
  id: string;
  institution_id: string;
  job_kind: string;
  operation_key: string;
  resource_id?: string | null;
  status: string;
  error_code?: string | null;
  error_detail?: string | null;
  attempt_count: number;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

// ==========================================
// Phase 6: Documents, Publication & Registration
// ==========================================

export type DocumentType = "resume" | "marksheet" | "college_id";
export type ReadinessStatus = "ready" | "pending" | "blocked" | "needs_review";

export interface RequirementCreate {
  document_type: DocumentType;
  display_label: string;
  allowed_extensions: Array<"pdf" | "docx">;
  max_size_bytes?: number;
  filename_pattern?: string | null;
  required_stage: "registration" | "scheduling";
  due_at?: string | null;
}

export interface RequirementResponse extends RequirementCreate {
  id: string;
  drive_id: string;
  drive_revision_id: string;
  max_size_bytes: number;
  created_at: string;
}

export interface PublicationProposalResponse {
  id: string;
  drive_id: string;
  drive_revision_id: string;
  evaluation_run_id: string;
  revision_number: number;
  canonical_hash: string;
  state: string;
  payload: Record<string, unknown>;
  dependencies: Record<string, unknown>;
  created_at: string;
}

export interface DocumentUploadSessionResponse {
  id: string;
  document_type: DocumentType;
  original_filename: string;
  upload_url: string;
  expires_at: string;
  status: string;
}

export interface FindingResponse {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
  required_action?: string | null;
}

export interface DocumentRevisionResponse {
  id: string;
  document_type: DocumentType;
  revision_number: number;
  original_filename: string;
  media_type: string;
  file_size_bytes: number;
  hash_sha256: string;
  scan_status: string;
  structure_status: string;
  text_status: string;
  created_at: string;
}

export interface RequirementReadinessResponse {
  requirement_id: string;
  document_type: DocumentType;
  display_label: string;
  required_stage: "registration" | "scheduling";
  due_at?: string | null;
  status: ReadinessStatus;
  findings: FindingResponse[];
  current_document?: DocumentRevisionResponse | null;
}

export interface DocumentReadinessResponse {
  status: ReadinessStatus;
  requirements: RequirementReadinessResponse[];
}

export interface RegistrationResponse {
  id: string;
  drive_id: string;
  student_profile_id: string;
  state: "draft" | "submitted" | "withdrawn" | "eligibility_hold";
  submitted_at?: string | null;
  withdrawn_at?: string | null;
  hold_reason?: string | null;
  concurrency_revision: number;
}

export interface StudentDriveResponse {
  drive_id: string;
  company_name: string;
  role_title: string;
  location?: string | null;
  work_mode: string;
  employment_type: string;
  compensation_details?: Record<string, unknown> | null;
  registration_start_at: string;
  registration_end_at: string;
  withdrawal_end_at?: string | null;
  eligibility_status: "eligible" | "ineligible" | "needs_review";
  eligibility_reasons: string[];
  document_readiness: DocumentReadinessResponse;
  registration?: RegistrationResponse | null;
}

export interface ParticipantResponse {
  student_profile_id: string;
  student_identifier: string;
  student_name: string;
  eligibility_status: string;
  readiness_status: ReadinessStatus;
  registration_state?: string | null;
  registration_id?: string | null;
  registration_revision?: number | null;
}

export interface ParticipantListResponse {
  items: ParticipantResponse[];
  total: number;
  counts: Record<string, number>;
}

// ==========================================
// Phase 7: Exact Communications & Safe Dispatch
// ==========================================

export type CommunicationKind =
  | "drive_announcement"
  | "missing_document_reminder"
  | "registration_deadline_reminder"
  | "clarification";
export type AudienceType =
  | "current_eligible"
  | "submitted_registrants"
  | "required_document_findings"
  | "explicit_recipients";

export interface AudienceRecipientResponse {
  id: string;
  student_profile_id: string;
  email: string;
  display_name: string;
  inclusion_reason: string;
  rendered_subject: string;
  rendered_body: string;
  rendered_hash: string;
}

export interface CommunicationDraftResponse {
  id: string;
  drive_id: string;
  revision_number: number;
  communication_kind: CommunicationKind;
  audience_type: AudienceType;
  subject_template: string;
  body_template: string;
  sender_email: string;
  reply_to: string;
  state: string;
  content_hash: string;
  audience_snapshot_id: string;
  audience_hash: string;
  included_count: number;
  excluded_count: number;
  duplicate_count: number;
  unresolved_count: number;
  exclusion_summary: Record<string, number>;
  recipients: AudienceRecipientResponse[];
  created_at: string;
}

export interface CommunicationProposalResponse {
  id: string;
  drive_id: string;
  draft: CommunicationDraftResponse;
  revision_number: number;
  canonical_hash: string;
  state: string;
  payload: Record<string, unknown>;
  dependencies: Record<string, unknown>;
  execution_expires_at?: string | null;
  sender_connection_revision?: string | null;
  decision?: Record<string, unknown> | null;
  created_at: string;
}

export interface DispatchOperationResponse {
  id: string;
  operation_key: string;
  recipient: string;
  recipient_name: string;
  status: string;
  attempt_count: number;
  provider_message_id?: string | null;
  last_error_code?: string | null;
}

export interface DispatchBatchResponse {
  id: string;
  drive_id: string;
  proposal_id: string;
  communication_draft_id: string;
  status: string;
  total_count: number;
  pending_count: number;
  accepted_count: number;
  delivered_count: number;
  failed_count: number;
  unknown_count: number;
  cancelled_count: number;
  execution_expires_at: string;
  operations: DispatchOperationResponse[];
  created_at: string;
}

export interface WorkflowRunResponse {
  id: string;
  drive_id: string;
  graph_version: string;
  state_schema_version: number;
  status: string;
  current_step: string;
  state_references: Record<string, unknown>;
  pending_proposal_id: string | null;
  pending_clarification_id: string | null;
  pending_case_id: string | null;
  last_event_id: string | null;
  last_processed_command_id: string | null;
  error_category: string | null;
  error_detail: string | null;
  concurrency_revision: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowCommandResponse {
  id: string;
  workflow_run_id: string;
  command_type: string;
  reference_type: string | null;
  reference_id: string | null;
  status: string;
  created_at: string;
}

export interface ExceptionCaseResponse {
  id: string;
  drive_id: string;
  workflow_run_id: string | null;
  category: string;
  severity: string;
  status: string;
  affected_resources: Array<Record<string, unknown>>;
  evidence: Record<string, unknown>;
  proposed_next_action: string;
  owner_membership_id: string | null;
  resolution_history: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
}

// ==========================================
// Phase 9: Scheduling, Results & Closure
// ==========================================

export interface RecruitmentRoundResponse {
  id: string;
  drive_id: string;
  sequence_number: number;
  name: string;
  round_type: string;
  requires_previous_round_outcome: boolean;
  status: string;
}

export interface RecruitmentSessionResponse {
  id: string;
  drive_id: string;
  round_id: string;
  status: string;
  current_revision_id: string | null;
  published_revision_id: string | null;
  revision: {
    id: string;
    revision_number: number;
    start_at: string;
    end_at: string;
    timezone: string;
    buffer_minutes: number;
    capacity: number;
    venue: string | null;
    meeting_url: string | null;
    panel_members: string[];
    change_reason: string | null;
  } | null;
  assignments: Array<{ student_profile_id: string; status: string; document_override_reason: string | null }>;
}

export interface LifecycleProposalResponse {
  id: string;
  action_type: string;
  target_type: string;
  target_id: string;
  revision_number: number;
  canonical_hash: string;
  state: string;
  payload: Record<string, unknown>;
  dependencies: Record<string, unknown>;
}

export interface DriveReportResponse {
  id: string;
  drive_id: string;
  revision_number: number;
  report_kind: string;
  status: string;
  snapshot_payload: Record<string, unknown>;
  snapshot_hash: string;
  reason: string;
  created_at: string;
}

export interface OutcomeRevisionResponse {
  id: string;
  round_id: string;
  student_profile_id: string;
  revision_number: number;
  outcome: string;
  source_type: string;
  source_reference: string;
  source_evidence: Record<string, unknown>;
  note: string | null;
  offer_status: string;
  acceptance_status: string;
  joining_status: string;
  published_at: string | null;
}

export interface StudentScheduleResult {
  drive_id: string;
  session_id: string;
  round: string;
  start_at: string;
  end_at: string;
  timezone: string;
  venue: string | null;
  meeting_url: string | null;
  outcome: { outcome: string; revision_number: number; offer_status: string; acceptance_status: string; joining_status: string } | null;
}
