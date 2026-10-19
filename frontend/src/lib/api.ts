export type Strategy = "memory_first" | "cold_search";
export type RouteUsed = "memory" | "live_search" | "cold_search" | "no_evidence";

export interface Repository { repository_id: string; name: string; snapshot_id: string }
export interface EvidencePointer { path: string; start_line: number; end_line: number }
export interface ArchitectureClaim {
  claim_id: string;
  title: string;
  text: string;
  keywords: string[];
  status: "valid" | "stale" | "unknown";
  evidence: EvidencePointer[];
}
export interface ArchitectureMemory {
  repository_id: string;
  snapshot_id: string;
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
  memory: (id: string) => api<ArchitectureMemory>(`/repositories/${encodeURIComponent(id)}/memory`),
  benchmarks: () => api<BenchmarkSummary>("/benchmarks/summary"),
  ask: (question: string, strategy: Strategy, repository_id: string) => api<QAResponse>("/qa/ask", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, strategy, repository_id }),
  }),
};
