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
    return this.request("/api/v1/students/import/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ csv_data: csvContent }),
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
    return this.request("/api/v1/students/import/commit", {
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
}

export const api = new PlacementOSClient();
