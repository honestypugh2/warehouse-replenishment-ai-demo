import { useState } from "react";
import { api } from "../api";
import type { Recommendation } from "../types";
import { APPROVER_UPN, decisionMeta, delta } from "./shared";

type Outcome =
  | { kind: "idle" }
  | { kind: "pending" }
  | { kind: "approved"; auditId: string }
  | { kind: "rejected"; auditId: string }
  | { kind: "error"; message: string };

export function RecommendationCard({ rec }: { rec: Recommendation }) {
  const [outcome, setOutcome] = useState<Outcome>({ kind: "idle" });
  const c = rec.candidate;
  const meta = decisionMeta[rec.decision];
  const blocked = rec.decision === "reject";

  async function approve() {
    setOutcome({ kind: "pending" });
    try {
      const res = await api.approve({
        sku: c.sku,
        facility: c.facility,
        new_min: c.recommended_min,
        new_max: c.recommended_max,
        approver_upn: APPROVER_UPN,
        rationale: rec.explanation,
      });
      setOutcome({ kind: "approved", auditId: res.audit_id });
    } catch (e) {
      setOutcome({ kind: "error", message: (e as Error).message });
    }
  }

  async function reject() {
    setOutcome({ kind: "pending" });
    try {
      const reason = blocked
        ? rec.validation.reasons.join(" ")
        : "Deferred by planner.";
      const res = await api.reject({
        sku: c.sku,
        facility: c.facility,
        approver_upn: APPROVER_UPN,
        reason,
      });
      setOutcome({ kind: "rejected", auditId: res.audit_id });
    } catch (e) {
      setOutcome({ kind: "error", message: (e as Error).message });
    }
  }

  return (
    <article className={`card ${blocked ? "card-blocked" : ""}`}>
      <header className="card-head">
        <div>
          <span className="sku">{c.sku}</span>
          <span className="loc">
            {c.facility} · {c.location}
          </span>
        </div>
        <span className={meta.className}>{meta.label}</span>
      </header>

      <div className="minmax">
        <div className="mm-col">
          <span className="mm-label">Min</span>
          <span className="mm-val">
            {c.current_min} → <strong>{c.recommended_min}</strong>
          </span>
          <span className="mm-delta">{delta(c.current_min, c.recommended_min)}</span>
        </div>
        <div className="mm-col">
          <span className="mm-label">Max</span>
          <span className="mm-val">
            {c.current_max} → <strong>{c.recommended_max}</strong>
          </span>
          <span className="mm-delta">{delta(c.current_max, c.recommended_max)}</span>
        </div>
        <div className="mm-col">
          <span className="mm-label">Confidence</span>
          <div className="conf-bar">
            <div
              className="conf-fill"
              style={{ width: `${Math.round(c.confidence * 100)}%` }}
            />
          </div>
          <span className="mm-delta">{Math.round(c.confidence * 100)}%</span>
        </div>
      </div>

      <p className="explanation">{rec.explanation}</p>

      {blocked && rec.validation.blocking_wave_id && (
        <div className="evidence">
          <strong>Validator evidence:</strong> wave{" "}
          <code>{rec.validation.blocking_wave_id}</code>
          {rec.validation.blocking_orders.length > 0 && (
            <> · open orders {rec.validation.blocking_orders.join(", ")}</>
          )}
        </div>
      )}

      <div className="citations">
        {rec.citations.map((cit) => (
          <code key={cit} className="cite">
            {cit}
          </code>
        ))}
      </div>

      <footer className="card-actions">
        {outcome.kind === "approved" && (
          <span className="result result-ok">
            Written to D365 · audit {outcome.auditId}
          </span>
        )}
        {outcome.kind === "rejected" && (
          <span className="result result-defer">
            Deferred · audit {outcome.auditId}
          </span>
        )}
        {outcome.kind === "error" && (
          <span className="result result-err">{outcome.message}</span>
        )}
        {(outcome.kind === "idle" || outcome.kind === "pending") && (
          <>
            <button
              className="btn btn-primary"
              disabled={blocked || outcome.kind === "pending"}
              onClick={approve}
              title={blocked ? "Blocked by the operational validator" : undefined}
            >
              Approve
            </button>
            <button
              className="btn btn-ghost"
              disabled={outcome.kind === "pending"}
              onClick={reject}
            >
              {blocked ? "Defer" : "Reject"}
            </button>
          </>
        )}
      </footer>
    </article>
  );
}
