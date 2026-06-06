import { useState } from "react";
import { api } from "../api";
import type { FoundryMode, SequentialRunResult } from "../types";
import { FACILITIES } from "./shared";
import { RecommendationCard } from "./RecommendationCard";

export function SequentialView({ mode }: { mode: FoundryMode }) {
  const [facility, setFacility] = useState<string>(FACILITIES[0]);
  const [data, setData] = useState<SequentialRunResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setData(await api.sequential(facility, mode));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const counts = data
    ? {
        total: data.count,
        passed: data.recommendations.filter((r) => r.validation.passed).length,
        blocked: data.recommendations.filter((r) => !r.validation.passed).length,
      }
    : null;

  return (
    <section>
      <div className="toolbar">
        <label>
          Facility
          <select value={facility} onChange={(e) => setFacility(e.target.value)}>
            {FACILITIES.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </label>
        <button className="btn btn-primary" onClick={run} disabled={loading}>
          {loading ? "Running workflow…" : "Run daily replen review"}
        </button>
        <p className="hint">
          Copilot Studio → Foundry sequential workflow → Databricks → D365
        </p>
      </div>

      {error && <div className="banner banner-err">{error}</div>}

      {counts && (
        <div className="summary">
          <span>
            <strong>{counts.total}</strong> candidates
          </span>
          <span className="ok">
            <strong>{counts.passed}</strong> passed validation
          </span>
          <span className="bad">
            <strong>{counts.blocked}</strong> blocked
          </span>
        </div>
      )}

      <div className="grid">
        {data?.recommendations.map((rec) => (
          <RecommendationCard key={rec.candidate.sku} rec={rec} />
        ))}
      </div>

      {!data && !loading && (
        <p className="empty">
          Pick a facility and run the review to see governed recommendations.
        </p>
      )}
    </section>
  );
}
