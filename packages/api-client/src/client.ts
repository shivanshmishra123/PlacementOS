import type {
  HealthResponse,
  ReadinessResponse,
  ErrorResponse,
  UserProfileResponse,
  DevLoginRequest,
  DevLoginResponse,
  PersonaInfo,
  StudentListItemDTO,
  StudentDetailDTO,
  CorrectionProposalDTO,
  CompanyCreate,
  CompanyResponse,
  DriveCreate,
  DriveUpdate,
  DriveRevisionCreate,
  DriveRevisionResponse,
  DriveResponse,
  DriveListResponse,
  UploadSessionCreate,
  UploadSessionResponse,
  PastedSourceCreate,
  SourceArtifactResponse,
  TextExtractionResponse,
  DownloadUrlResponse,
  DomainJobResponse,
  EvidenceLocator,
  InterpretationResponse,
  PolicyResponse,
  ProposalResponse,
  DecisionResponse,
  EvaluationRunResponse,
  StudentEligibilityResponse,
  EligibilityReviewRequestResponse,
  DocumentType,
  RequirementCreate,
  RequirementResponse,
  PublicationProposalResponse,
  DocumentUploadSessionResponse,
  DocumentRevisionResponse,
  StudentDriveResponse,
  RegistrationResponse,
  ParticipantListResponse,
  CommunicationKind,
  AudienceType,
  CommunicationDraftResponse,
  CommunicationProposalResponse,
  DispatchBatchResponse,
  DispatchOperationResponse,
  WorkflowRunResponse,
  ExceptionCaseResponse,
} from "./types";

export class ApiError extends Error {
  public readonly code: string;
  public readonly correlationId?: string | null;
  public readonly details: Record<string, unknown>;
  public readonly status: number;

  constructor(status: number, errorResponse: ErrorResponse) {
    super(errorResponse.error.message);
    this.name = "ApiError";
    this.status = status;
    this.code = errorResponse.error.code;
    this.correlationId = errorResponse.error.correlation_id;
    this.details = errorResponse.error.details || {};
  }
}

export class PlacementOSClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers = new Headers(options.headers);
    headers.set("Accept", "application/json");
    const method = (options.method || "GET").toUpperCase();
    if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method) && typeof document !== "undefined") {
      const csrf = document.cookie
        .split("; ")
        .find((entry) => entry.startsWith("csrf_token="))
        ?.split("=")
        .slice(1)
        .join("=");
      if (csrf) headers.set("X-CSRF-Token", decodeURIComponent(csrf));
    }

    const response = await fetch(url, {
      ...options,
      headers,
      credentials: "include", // Enable cookie transport
    });

    if (!response.ok) {
      let errorBody: ErrorResponse;
      try {
        errorBody = (await response.json()) as ErrorResponse;
      } catch {
        errorBody = {
          error: {
            code: "HTTP_ERROR",
            message: `Request failed with HTTP status ${response.status}`,
          },
        };
      }
      throw new ApiError(response.status, errorBody);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  }

  // ==========================================
  // Health & Diagnostics
  // ==========================================

  public async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/api/v1/health");
  }

  public async getReadiness(): Promise<ReadinessResponse> {
    return this.request<ReadinessResponse>("/api/v1/ready");
  }

  // ==========================================
  // Authentication & Personas
  // ==========================================

  public async devLogin(req: DevLoginRequest): Promise<DevLoginResponse> {
    return this.request<DevLoginResponse>("/api/v1/auth/dev-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  public async listPersonas(): Promise<PersonaInfo[]> {
    return this.request<PersonaInfo[]>("/api/v1/auth/personas");
  }

  /** Get profile and active institutional scope of authenticated user. */
  public async getMe(): Promise<UserProfileResponse> {
    return this.request<UserProfileResponse>("/api/v1/auth/me");
  }

  public async getCurrentUser(): Promise<UserProfileResponse> {
    return this.getMe();
  }

  public async logout(): Promise<{ message: string }> {
    return this.request<{ message: string }>("/api/v1/auth/logout", {
      method: "POST",
    });
  }

  // ==========================================
  // Students & Academic Records (Phase 2)
  // ==========================================

  public async listStudents(params?: {
    branch?: string;
    min_cgpa?: number;
    graduation_year?: number;
  }): Promise<StudentListItemDTO[]> {
    const searchParams = new URLSearchParams();
    if (params?.branch) searchParams.set("branch", params.branch);
    if (params?.min_cgpa !== undefined) searchParams.set("min_cgpa", String(params.min_cgpa));
    if (params?.graduation_year !== undefined)
      searchParams.set("graduation_year", String(params.graduation_year));

    const qs = searchParams.toString();
    return this.request<StudentListItemDTO[]>(`/api/v1/students${qs ? `?${qs}` : ""}`);
  }

  public async getStudent(studentId: string): Promise<StudentDetailDTO> {
    return this.request<StudentDetailDTO>(`/api/v1/students/${studentId}`);
  }

  public async getStudentDetail(studentId: string): Promise<StudentDetailDTO> {
    return this.getStudent(studentId);
  }

  public async previewCsv(csvContent: string): Promise<{
    preview_token: string;
    total_rows: number;
    valid_rows_count: number;
    invalid_rows_count: number;
    new_students_count: number;
    updating_students_count: number;
    sample_rows: Record<string, unknown>[];
    invalid_rows: Record<string, unknown>[];
  }> {
    return this.request("/api/v1/students/import-preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ csv_content: csvContent }),
    });
  }

  public async commitCsv(previewToken: string): Promise<{
    message: string;
    total_committed: number;
    created_students: number;
    updated_students: number;
    inserted_count?: number;
    updated_count?: number;
  }> {
    return this.request("/api/v1/students/import-commit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preview_token: previewToken }),
    });
  }

  public async getMyStudentProfile(): Promise<StudentDetailDTO> {
    return this.request<StudentDetailDTO>("/api/v1/student/me");
  }

  public async submitCorrection(req: {
    proposed_changes: Record<string, unknown>;
    justification: string;
    supporting_document_url?: string;
  }): Promise<CorrectionProposalDTO> {
    return this.request<CorrectionProposalDTO>("/api/v1/student/corrections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  public async getMyCorrections(): Promise<CorrectionProposalDTO[]> {
    return this.request<CorrectionProposalDTO[]>("/api/v1/student/corrections");
  }

  public async listPendingCorrections(): Promise<CorrectionProposalDTO[]> {
    return this.request<CorrectionProposalDTO[]>("/api/v1/students/corrections/pending");
  }

  public async decideCorrection(
    proposalId: string,
    decision: "approved" | "rejected",
    reviewNotes?: string
  ): Promise<CorrectionProposalDTO> {
    return this.request<CorrectionProposalDTO>(
      `/api/v1/students/corrections/${proposalId}/decide`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, review_notes: reviewNotes }),
      }
    );
  }

  // ==========================================
  // Recruitment Drives & Companies (Phase 3)
  // ==========================================

  public async listCompanies(): Promise<CompanyResponse[]> {
    return this.request<CompanyResponse[]>("/api/v1/companies");
  }

  public async createCompany(req: CompanyCreate): Promise<CompanyResponse> {
    return this.request<CompanyResponse>("/api/v1/companies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  public async listDrives(params?: {
    status?: string;
    company_id?: string;
    page?: number;
    limit?: number;
  }): Promise<DriveListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.company_id) searchParams.set("company_id", params.company_id);
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.limit) searchParams.set("limit", String(params.limit));

    const qs = searchParams.toString();
    return this.request<DriveListResponse>(`/api/v1/drives${qs ? `?${qs}` : ""}`);
  }

  public async getDrive(driveId: string): Promise<DriveResponse> {
    return this.request<DriveResponse>(`/api/v1/drives/${driveId}`);
  }

  public async createDrive(req: DriveCreate): Promise<DriveResponse> {
    return this.request<DriveResponse>("/api/v1/drives", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  public async updateDrive(driveId: string, req: DriveUpdate): Promise<DriveResponse> {
    return this.request<DriveResponse>(`/api/v1/drives/${driveId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  public async createDriveRevision(
    driveId: string,
    req: DriveRevisionCreate
  ): Promise<DriveRevisionResponse> {
    return this.request<DriveRevisionResponse>(`/api/v1/drives/${driveId}/revisions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  // ==========================================
  // Storage, Intake & Extractions (Phase 3)
  // ==========================================

  public async createUploadSession(req: UploadSessionCreate): Promise<UploadSessionResponse> {
    return this.request<UploadSessionResponse>("/api/v1/uploads/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  public async completeUploadSession(sessionId: string): Promise<SourceArtifactResponse> {
    return this.request<SourceArtifactResponse>(`/api/v1/uploads/sessions/${sessionId}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
  }

  public async createPastedSource(
    driveId: string,
    req: PastedSourceCreate
  ): Promise<SourceArtifactResponse> {
    return this.request<SourceArtifactResponse>(`/api/v1/drives/${driveId}/sources/pasted`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  public async getSourceArtifact(artifactId: string): Promise<SourceArtifactResponse> {
    return this.request<SourceArtifactResponse>(`/api/v1/sources/${artifactId}`);
  }

  public async getTextExtraction(artifactId: string): Promise<TextExtractionResponse> {
    return this.request<TextExtractionResponse>(`/api/v1/sources/${artifactId}/extractions`);
  }

  public async getDownloadUrl(artifactId: string): Promise<DownloadUrlResponse> {
    return this.request<DownloadUrlResponse>(`/api/v1/sources/${artifactId}/download-url`);
  }

  public async retriggerExtraction(artifactId: string): Promise<DomainJobResponse> {
    return this.request<DomainJobResponse>(`/api/v1/sources/${artifactId}/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
  }

  public async getJob(jobId: string): Promise<DomainJobResponse> {
    return this.request<DomainJobResponse>(`/api/v1/jobs/${jobId}`);
  }

  // ==========================================
  // JD Intelligence & Policy Review (Phase 4)
  // ==========================================

  public async createInterpretation(
    driveId: string,
    req: {
      source_artifact_id: string;
      mode?: "fixture" | "manual";
      manual_facts?: Record<string, unknown>;
      manual_evidence?: EvidenceLocator[];
      rationale?: string;
    }
  ): Promise<InterpretationResponse> {
    return this.request<InterpretationResponse>(`/api/v1/drives/${driveId}/interpretations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  public async listInterpretations(driveId: string): Promise<InterpretationResponse[]> {
    return this.request<InterpretationResponse[]>(`/api/v1/drives/${driveId}/interpretations`);
  }

  public async correctInterpretation(
    interpretationId: string,
    req: { field_path: string; corrected_value: unknown; rationale: string; evidence?: EvidenceLocator }
  ): Promise<InterpretationResponse> {
    return this.request<InterpretationResponse>(`/api/v1/interpretations/${interpretationId}/corrections`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  public async resolveClarification(
    clarificationId: string,
    value: unknown,
    rationale: string
  ): Promise<InterpretationResponse> {
    return this.request<InterpretationResponse>(`/api/v1/clarifications/${clarificationId}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value, rationale }),
    });
  }

  public async compilePolicy(
    driveId: string,
    interpretationId: string,
    explicitlyNotRequired: string[] = []
  ): Promise<PolicyResponse> {
    return this.request<PolicyResponse>(`/api/v1/drives/${driveId}/policies`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        interpretation_id: interpretationId,
        explicitly_not_required: explicitlyNotRequired,
      }),
    });
  }

  public async listPolicies(driveId: string): Promise<PolicyResponse[]> {
    return this.request<PolicyResponse[]>(`/api/v1/drives/${driveId}/policies`);
  }

  public async submitPolicyReview(policyId: string): Promise<ProposalResponse> {
    return this.request<ProposalResponse>(`/api/v1/policies/${policyId}/submit-review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
  }

  public async getProposal(proposalId: string): Promise<ProposalResponse> {
    return this.request<ProposalResponse>(`/api/v1/proposals/${proposalId}`);
  }

  public async decideProposal(
    proposalId: string,
    req: {
      expected_revision: number;
      expected_hash: string;
      decision: "approved" | "rejected" | "revision_requested";
      comment?: string;
    }
  ): Promise<DecisionResponse> {
    return this.request<DecisionResponse>(`/api/v1/proposals/${proposalId}/decisions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  // ==========================================
  // Deterministic Eligibility (Phase 5)
  // ==========================================

  public async createEvaluationRun(
    driveId: string,
    policyId?: string
  ): Promise<EvaluationRunResponse> {
    return this.request<EvaluationRunResponse>(`/api/v1/drives/${driveId}/evaluations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy_id: policyId }),
    });
  }

  public async listEvaluationRuns(driveId: string): Promise<EvaluationRunResponse[]> {
    return this.request<EvaluationRunResponse[]>(`/api/v1/drives/${driveId}/evaluations`);
  }

  public async getEvaluationRun(
    runId: string,
    outcome?: "eligible" | "ineligible" | "needs_review"
  ): Promise<EvaluationRunResponse> {
    const query = outcome ? `?outcome=${outcome}` : "";
    return this.request<EvaluationRunResponse>(`/api/v1/evaluation-runs/${runId}${query}`);
  }

  public async getMyEligibility(): Promise<StudentEligibilityResponse[]> {
    return this.request<StudentEligibilityResponse[]>("/api/v1/student/eligibility");
  }

  public async requestEligibilityReview(
    resultId: string,
    reason: string
  ): Promise<EligibilityReviewRequestResponse> {
    return this.request<EligibilityReviewRequestResponse>(
      `/api/v1/student/eligibility/${resultId}/review-request`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      }
    );
  }

  public async listEligibilityReviewRequests(
    driveId: string
  ): Promise<EligibilityReviewRequestResponse[]> {
    return this.request<EligibilityReviewRequestResponse[]>(
      `/api/v1/drives/${driveId}/eligibility-review-requests`
    );
  }

  // ==========================================
  // Documents, Publication & Registration (Phase 6)
  // ==========================================

  public async setDocumentRequirements(
    driveId: string,
    expectedDriveRevision: number,
    requirements: RequirementCreate[]
  ): Promise<RequirementResponse[]> {
    return this.request<RequirementResponse[]>(`/api/v1/drives/${driveId}/document-requirements`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_drive_revision: expectedDriveRevision, requirements }),
    });
  }

  public async listDocumentRequirements(driveId: string): Promise<RequirementResponse[]> {
    return this.request<RequirementResponse[]>(`/api/v1/drives/${driveId}/document-requirements`);
  }

  public async createPublicationProposal(
    driveId: string,
    request: {
      expected_drive_revision: number;
      evaluation_run_id: string;
      registration_start_at: string;
      registration_end_at: string;
      withdrawal_end_at?: string | null;
    }
  ): Promise<PublicationProposalResponse> {
    return this.request<PublicationProposalResponse>(`/api/v1/drives/${driveId}/publication-proposals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  }

  public async decidePublicationProposal(
    proposalId: string,
    request: { expected_revision: number; expected_hash: string; decision: "approved" | "rejected" | "revision_requested"; comment?: string }
  ): Promise<PublicationProposalResponse> {
    return this.request<PublicationProposalResponse>(`/api/v1/publication-proposals/${proposalId}/decisions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  }

  public async createDocumentUploadSession(
    documentType: DocumentType,
    file: File
  ): Promise<DocumentUploadSessionResponse> {
    return this.request<DocumentUploadSessionResponse>("/api/v1/student/documents/upload-sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_type: documentType,
        original_filename: file.name,
        content_type: file.type || "application/octet-stream",
        byte_size: file.size,
      }),
    });
  }

  public async uploadStudentDocument(documentType: DocumentType, file: File): Promise<DocumentRevisionResponse> {
    const upload = await this.createDocumentUploadSession(documentType, file);
    const response = await fetch(upload.upload_url, {
      method: "PUT",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: file,
    });
    if (!response.ok) throw new Error(`Private upload failed with status ${response.status}`);
    return this.request<DocumentRevisionResponse>(`/api/v1/student/documents/upload-sessions/${upload.id}/complete`, {
      method: "POST",
    });
  }

  public async listMyDocuments(): Promise<DocumentRevisionResponse[]> {
    return this.request<DocumentRevisionResponse[]>("/api/v1/student/documents");
  }

  public async getMyDocumentDownloadUrl(revisionId: string): Promise<DownloadUrlResponse> {
    return this.request<DownloadUrlResponse>(`/api/v1/student/documents/${revisionId}/download-url`);
  }

  public async listStudentDrives(): Promise<StudentDriveResponse[]> {
    return this.request<StudentDriveResponse[]>("/api/v1/student/drives");
  }

  public async saveRegistrationDraft(driveId: string): Promise<RegistrationResponse> {
    return this.request<RegistrationResponse>(`/api/v1/student/drives/${driveId}/registrations/draft`, { method: "POST" });
  }

  public async submitRegistration(driveId: string): Promise<RegistrationResponse> {
    return this.request<RegistrationResponse>(`/api/v1/student/drives/${driveId}/registrations`, { method: "POST" });
  }

  public async withdrawRegistration(registrationId: string, expectedRevision: number, reason: string): Promise<RegistrationResponse> {
    return this.request<RegistrationResponse>(`/api/v1/student/registrations/${registrationId}/withdraw`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_revision: expectedRevision, reason }),
    });
  }

  public async listParticipants(
    driveId: string,
    filters: { eligibility_status?: string; readiness_status?: string; registration_state?: string } = {}
  ): Promise<ParticipantListResponse> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
    const query = params.toString();
    return this.request<ParticipantListResponse>(`/api/v1/drives/${driveId}/participants${query ? `?${query}` : ""}`);
  }

  public async coordinatorRegistrationAction(
    registrationId: string,
    expectedRevision: number,
    action: "restore" | "withdraw",
    reason: string
  ): Promise<RegistrationResponse> {
    return this.request<RegistrationResponse>(`/api/v1/registrations/${registrationId}/coordinator-action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_revision: expectedRevision, action, reason }),
    });
  }

  public getParticipantExportUrl(driveId: string): string {
    return `${this.baseUrl}/api/v1/drives/${driveId}/participants.csv`;
  }

  // ==========================================
  // Exact Communications & Safe Dispatch (Phase 7)
  // ==========================================

  public async createCommunicationDraft(
    driveId: string,
    request: {
      communication_kind: CommunicationKind;
      audience_type: AudienceType;
      explicit_student_ids?: string[];
      subject_template?: string;
      body_template?: string;
      sender_email?: string;
      reply_to: string;
    }
  ): Promise<CommunicationDraftResponse> {
    return this.request<CommunicationDraftResponse>(`/api/v1/drives/${driveId}/communication-drafts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  }

  public async listCommunicationDrafts(driveId: string): Promise<CommunicationDraftResponse[]> {
    return this.request<CommunicationDraftResponse[]>(`/api/v1/drives/${driveId}/communication-drafts`);
  }

  public async submitCommunicationReview(
    draftId: string,
    executionExpiresAt: string
  ): Promise<CommunicationProposalResponse> {
    return this.request<CommunicationProposalResponse>(`/api/v1/communication-drafts/${draftId}/submit-review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ execution_expires_at: executionExpiresAt }),
    });
  }

  public async listCommunicationProposals(): Promise<CommunicationProposalResponse[]> {
    return this.request<CommunicationProposalResponse[]>("/api/v1/communication-proposals");
  }

  public async decideCommunicationProposal(
    proposalId: string,
    request: {
      expected_revision: number;
      expected_hash: string;
      decision: "approved" | "rejected" | "revision_requested";
      comment?: string;
    }
  ): Promise<CommunicationProposalResponse> {
    return this.request<CommunicationProposalResponse>(`/api/v1/communication-proposals/${proposalId}/decisions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  }

  public async listDispatchBatches(): Promise<DispatchBatchResponse[]> {
    return this.request<DispatchBatchResponse[]>("/api/v1/dispatch-batches");
  }

  public async cancelDispatchBatch(batchId: string, reason: string): Promise<DispatchBatchResponse> {
    return this.request<DispatchBatchResponse>(`/api/v1/dispatch-batches/${batchId}/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
  }

  public async reconcileDispatchOperation(
    operationId: string,
    resolution: "provider_accepted" | "confirmed_not_accepted",
    evidence: string
  ): Promise<DispatchOperationResponse> {
    return this.request<DispatchOperationResponse>(`/api/v1/dispatch-operations/${operationId}/reconcile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resolution, evidence }),
    });
  }

  // ==========================================
  // Durable Workflows & Baseline Cases (Phase 8)
  // ==========================================

  public async startWorkflowRun(
    driveId: string,
    sourceArtifactId?: string
  ): Promise<WorkflowRunResponse> {
    return this.request<WorkflowRunResponse>(`/api/v1/drives/${driveId}/workflow-runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_artifact_id: sourceArtifactId || null }),
    });
  }

  public async listWorkflowRuns(driveId: string): Promise<WorkflowRunResponse[]> {
    return this.request<WorkflowRunResponse[]>(`/api/v1/drives/${driveId}/workflow-runs`);
  }

  public async getWorkflowRun(workflowRunId: string): Promise<WorkflowRunResponse> {
    return this.request<WorkflowRunResponse>(`/api/v1/workflow-runs/${workflowRunId}`);
  }

  public async placeWorkflowHold(
    workflowRunId: string,
    expectedRevision: number,
    reason: string
  ): Promise<WorkflowRunResponse> {
    return this.request<WorkflowRunResponse>(`/api/v1/workflow-runs/${workflowRunId}/hold`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_run_revision: expectedRevision, reason }),
    });
  }

  public async releaseWorkflowHold(
    workflowRunId: string,
    expectedRevision: number,
    reason: string
  ): Promise<WorkflowRunResponse> {
    return this.request<WorkflowRunResponse>(`/api/v1/workflow-runs/${workflowRunId}/release-hold`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_run_revision: expectedRevision, reason }),
    });
  }

  public async listExceptionCases(status?: string): Promise<ExceptionCaseResponse[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    return this.request<ExceptionCaseResponse[]>(`/api/v1/exception-cases${query}`);
  }

  public async actOnExceptionCase(
    caseId: string,
    action: "acknowledged" | "resolved" | "dismissed",
    note: string,
    expectedRunRevision?: number
  ): Promise<ExceptionCaseResponse> {
    return this.request<ExceptionCaseResponse>(`/api/v1/exception-cases/${caseId}/actions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        note,
        expected_run_revision: expectedRunRevision || null,
      }),
    });
  }
}

export const api = new PlacementOSClient();
