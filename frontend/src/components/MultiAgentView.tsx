import { useMemo, useState } from "react";
import { api } from "../api";
import type { FoundryMode, MultiAgentRunResult } from "../types";
import { APPROVER_UPN, FACILITIES, decisionMeta } from "./shared";

export function MultiAgentView({ mode }: { mode: FoundryMode }) {
  const [selected, setSelected] = useState<string[]>([...FACILITIES]);
  const [data, setData] = useState<MultiAgentRunResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [approved, setApproved] = useState<Set<string>>(new Set());

  function toggle(f: string) {
    setSelected((prev) =>
      prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f],
    );
  }

  async function run() {
    if (selected.length === 0) return;
    setLoading(true);
    setError(null);
    setApproved(new Set());
    try {
      setData(await api.multiagent(selected, mode));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const approvable = useMemo(
    () =>
      (data?.ranking ?? []).filter((r) => r.decision === "approve_suggested"),
    [data],
  );

  async function bulkApprove() {
    if (!data) return;
    const next = new Set(approved);
    for (const item of approvable) {
      try {
        await api.approve({
          sku: item.sku,
          facility: item.facility,
          new_min: 0,
          new_max: 1, // demo bulk-approve uses validated candidates server-side
          approver_upn: APPROVER_UPN,
          rationale: item.explanation,
        });
        next.add(`${item.facility}:${item.sku}`);
      } catch {
        /* surfaced per-row below */
      }
    }
    setApproved(new Set(next));
  }

  return (
    <section>
      <div className="toolbar">
        <div className="facility-pills">
          {FACILITIES.map((f) => (
            <button
              key={f}
              className={`chip ${selected.includes(f) ? "chip-on" : ""}`}
              onClick={() => toggle(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <button
          className="btn btn-primary"
          onClick={run}
          disabled={loading || selected.length === 0}
        >
          {loading ? "Planning…" : "Plan cross-facility changes"}
        </button>
        <p className="hint">
          Copilot Studio → Foundry orchestrator → Slotting · Forecast · Validator
          · Risk
        </p>
      </div>

      {error && <div className="banner banner-err">{error}</div>}

      {data && (
        <>
          <div className="summary">
            <span>
              Ranked top <strong>{data.ranking.length}</strong> across{" "}
              {data.facilities.join(", ")}
            </span>
            <button
              className="btn btn-primary sm"
              onClick={bulkApprove}
              disabled={approvable.length === 0}
            >
              Bulk-approve {approvable.length} high-confidence
            </button>
          </div>

          <table className="rank-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Facility</th>
                <th>SKU</th>
                <th>Score</th>
                <th>Decision</th>
                <th>Rationale</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.ranking.map((item, i) => {
                const key = `${item.facility}:${item.sku}`;
                const meta = decisionMeta[item.decision];
                return (
                  <tr key={key}>
                    <td>{i + 1}</td>
                    <td>{item.facility}</td>
                    <td className="mono">{item.sku}</td>
                    <td>{item.score.toFixed(1)}</td>
                    <td>
                      <span className={meta.className}>{meta.label}</span>
                    </td>
                    <td className="rationale">{item.explanation}</td>
                    <td>
                      {approved.has(key) ? (
                        <span className="result result-ok">Written</span>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}

      {!data && !loading && (
        <p className="empty">
          Select facilities and plan to see a ranked, cross-facility set of
          changes.
        </p>
      )}
    </section>
  );
}
