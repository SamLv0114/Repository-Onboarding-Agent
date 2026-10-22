export type Strategy = "memory_first" | "cold_search";
export type RouteUsed = "memory" | "live_search" | "cold_search" | "no_evidence";

export type RepositoryStatus = "ready" | "not_onboarded" | "queued" | "cloning" | "onboarding" | "failed";
export interface Repository {
  repository_id: string;
  name: string;
  url?: string | null;
  snapshot_id: string;
  source_available: boolean;
  memory_available: boolean;
  status: RepositoryStatus;
  progress?: { done: number; total: number } | null;
  error?: string | null;
}
export interface EvidencePointer { path: string; start_line: number; end_line: number; content_hash?: string }
export interface ArchitectureClaim {
  claim_id: string;
  title: string;
  text: string;
  keywords: string[];
  level: "repository" | "file";
  status: "valid" | "stale" | "unknown";
  evidence: EvidencePointer[];
}
export interface LLMUsage { llm_calls: number; input_tokens: number; output_tokens: number }
export interface BuildCost extends LLMUsage { model: string; elapsed_s: number }
export interface QAUsage extends LLMUsage { tool_calls: number }
export interface ArchitectureMemory {
  repository_id: string;
  snapshot_id: string;
  build_cost?: BuildCost | null;
  claims: ArchitectureClaim[];
}
export interface Citation extends EvidencePointer { preview: string }
export interface QAResponse {
  repository_id: string;
  question: string;
  answer: string;
  strategy_used: RouteUsed;
  citations: Citation[];
  matched_claim_ids: string[];
  is_demo: boolean;
  elapsed_ms: number;
  answer_status?: "answered" | "insufficient_evidence" | "invalid_citations" | "generation_error" | null;
  usage?: QAUsage | null;
  note?: string | null;
}
export interface BenchmarkSummary { available: boolean; message: string; metrics: unknown[] }

const API_ROOT = import.meta.env.VITE_API_BASE_URL || "/api";

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_ROOT}${path}`, options);
  } catch {
    throw new Error("Cannot reach FastAPI. Start the backend on http://localhost:8000.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as {detail?: string} | null;
    throw new Error(body?.detail || `API request failed (${response.status})`);
  }
  return await response.json() as T;
}

export const client = {
  health: () => api<{status: string}>("/health"),
  repositories: () => api<Repository[]>("/repositories"),
  repository: (id: string) => api<Repository>(`/repositories/${encodeURIComponent(id)}`),
  addRepository: (url: string) => api<Repository>("/repositories", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  }),
  memory: (id: string) => api<ArchitectureMemory>(`/repositories/${encodeURIComponent(id)}/memory`),
  benchmarks: () => api<BenchmarkSummary>("/benchmarks/summary"),
  ask: (question: string, strategy: Strategy, repository_id: string) => api<QAResponse>("/qa/ask", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, strategy, repository_id }),
  }),
};
