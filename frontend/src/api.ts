import type {
  ApprovalRequest,
  D365WriteResponse,
  FoundryMode,
  Health,
  MultiAgentRunResult,
  RejectionResponse,
  SequentialRunResult,
} from "./types";

// In dev, Vite proxies /api -> http://localhost:8080 (see vite.config.ts).
const BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => http<Health>("/health"),

  sequential: (facility: string, mode?: FoundryMode) =>
    http<SequentialRunResult>(
      `/recommendations/sequential?facility=${encodeURIComponent(facility)}` +
        (mode ? `&foundry=${mode}` : ""),
    ),

  multiagent: (facilities: string[], mode?: FoundryMode) => {
    const qs = facilities
      .map((f) => `facilities=${encodeURIComponent(f)}`)
      .join("&");
    return http<MultiAgentRunResult>(
      `/recommendations/multiagent?${qs}` + (mode ? `&foundry=${mode}` : ""),
    );
  },

  approve: (req: ApprovalRequest) =>
    http<D365WriteResponse>("/approve", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  reject: (req: {
    sku: string;
    facility: string;
    approver_upn: string;
    reason: string;
  }) =>
    http<RejectionResponse>("/approve/reject", {
      method: "POST",
      body: JSON.stringify(req),
    }),
};
