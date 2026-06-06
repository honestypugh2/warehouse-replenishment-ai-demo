import type { Decision } from "../types";

export const APPROVER_UPN = "planner@contoso.com";

export const FACILITIES = ["NJ-01", "CA-02"] as const;

export const decisionMeta: Record<
  Decision,
  { label: string; className: string }
> = {
  approve_suggested: { label: "Approve suggested", className: "pill pill-green" },
  needs_review: { label: "Needs review", className: "pill pill-amber" },
  reject: { label: "Blocked", className: "pill pill-red" },
};

export function delta(current: number, recommended: number): string {
  const diff = recommended - current;
  if (diff === 0) return "no change";
  return diff > 0 ? `+${diff}` : `${diff}`;
}
