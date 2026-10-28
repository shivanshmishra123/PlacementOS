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
