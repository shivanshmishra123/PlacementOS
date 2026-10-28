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

    return (await response.json()) as T;
  }

  /** Retrieve backend application liveness status. */
  public async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  /** Retrieve backend and dependency readiness status. */
  public async getReadiness(): Promise<ReadinessResponse> {
    return this.request<ReadinessResponse>("/ready");
  }

  /** List available development personas. */
  public async listPersonas(): Promise<PersonaInfo[]> {
    return this.request<PersonaInfo[]>("/api/v1/auth/personas");
  }

  /** Sign in using a development persona or email. */
  public async devLogin(req: DevLoginRequest): Promise<DevLoginResponse> {
    return this.request<DevLoginResponse>("/api/v1/auth/dev-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  /** Get profile and active institutional scope of authenticated user. */
  public async getMe(): Promise<UserProfileResponse> {
    return this.request<UserProfileResponse>("/api/v1/auth/me");
  }

  /** Revoke session and sign out. */
  public async logout(): Promise<{ message: string }> {
    return this.request<{ message: string }>("/api/v1/auth/logout", {
      method: "POST",
    });
  }

  /** List scoped student records with optional filters. */
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

  /** Get student record detail with revision history. */
  public async getStudentDetail(studentId: string): Promise<StudentDetailDTO> {
    return this.request<StudentDetailDTO>(`/api/v1/students/${studentId}`);
  }

  /** Preview CSV import without mutations. */
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

  /** Commit previewed CSV rows. */
  public async commitCsv(previewToken: string): Promise<{
    message: string;
    created_students: number;
    updated_students: number;
    total_committed: number;
  }> {
    return this.request("/api/v1/students/import-commit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preview_token: previewToken }),
    });
  }

  /** Get student's self-service profile. */
  public async getMyStudentProfile(): Promise<StudentDetailDTO> {
    return this.request<StudentDetailDTO>("/api/v1/student/me");
  }

  /** Submit student correction proposal. */
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

  /** List authenticated student's correction proposals with status. */
  public async getMyCorrections(): Promise<CorrectionProposalDTO[]> {
    return this.request<CorrectionProposalDTO[]>("/api/v1/student/corrections");
  }

  /** List pending correction proposals for coordinator review. */
  public async listPendingCorrections(): Promise<CorrectionProposalDTO[]> {
    return this.request<CorrectionProposalDTO[]>("/api/v1/students/corrections/pending");
  }

  /** Decide correction proposal (approve/reject). */
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
}

