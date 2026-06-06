// Data contracts mirrored from the FastAPI backend (app/models/schemas.py).

export type Decision = "approve_suggested" | "needs_review" | "reject";

export interface Candidate {
  sku: string;
  facility: string;
  location: string;
  current_min: number;
  current_max: number;
  recommended_min: number;
  recommended_max: number;
  rationale: string;
  confidence: number;
}

export interface ValidationResult {
  sku: string;
  passed: boolean;
  reasons: string[];
  blocking_wave_id: string | null;
  blocking_orders: string[];
}

export interface Recommendation {
  candidate: Candidate;
  validation: ValidationResult;
  decision: Decision;
  explanation: string;
  citations: string[];
}

export interface SequentialRunResult {
  facility: string;
  count: number;
  recommendations: Recommendation[];
}

export interface RankedItem {
  facility: string;
  sku: string;
  score: number;
  decision: Decision;
  explanation: string;
  citations: string[];
}

export interface MultiAgentRunResult {
  facilities: string[];
  ranking: RankedItem[];
}

export interface ApprovalRequest {
  sku: string;
  facility: string;
  new_min: number;
  new_max: number;
  approver_upn: string;
  rationale: string;
}

export interface D365WriteResponse {
  sku: string;
  facility: string;
  success: boolean;
  audit_id: string;
  message: string;
}

export interface RejectionResponse {
  sku: string;
  facility: string;
  deferred: boolean;
  audit_id: string;
  message: string;
}

export interface Health {
  ok: boolean;
  mock_mode: boolean;
  databricks_mode: string;
  d365_mode: string;
  foundry_mode: FoundryMode;
  foundry_live_available: boolean;
}

export type FoundryMode = "mock" | "live";
