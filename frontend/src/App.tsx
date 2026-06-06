import { useEffect, useState } from "react";
import { api } from "./api";
import type { FoundryMode, Health } from "./types";
import { SequentialView } from "./components/SequentialView";
import { MultiAgentView } from "./components/MultiAgentView";

type Tab = "sequential" | "multiagent";

export default function App() {
  const [tab, setTab] = useState<Tab>("sequential");
  const [health, setHealth] = useState<Health | null>(null);
  const [mode, setMode] = useState<FoundryMode>("mock");

  useEffect(() => {
    api
      .health()
      .then((h) => {
        setHealth(h);
        setMode(h.foundry_mode);
      })
      .catch(() => setHealth(null));
  }, []);

  const liveAvailable = health?.foundry_live_available ?? false;

  return (
    <div className="app">
      <header className="app-head">
        <div className="brand">
          <h1>AI Warehouse Replenishment Orchestration</h1>
          <p>
            Governed, human-in-the-loop min-max review · Copilot Studio · Foundry
            · Databricks · D365
          </p>
        </div>
        <div className="status">
          {health ? (
            <div className="mode-switch" role="group" aria-label="Foundry mode">
              <button
                className={`mode-opt ${mode === "mock" ? "mode-on" : ""}`}
                onClick={() => setMode("mock")}
                title="Everything mocked — no Azure calls, fully offline."
              >
                Mock
              </button>
              <button
                className={`mode-opt ${mode === "live" ? "mode-on" : ""}`}
                onClick={() => liveAvailable && setMode("live")}
                disabled={!liveAvailable}
                title={
                  liveAvailable
                    ? "Real Azure AI Foundry reasoning · mock data, Databricks & D365."
                    : "Live Foundry not configured on the server."
                }
              >
                Live Foundry
              </button>
            </div>
          ) : (
            <span className="badge badge-off">API offline</span>
          )}
        </div>
      </header>

      <div className="mode-note">
        {mode === "live" ? (
          <span>
            <strong>Live Foundry:</strong> recommendations are narrated by a real
            Azure AI Foundry model. Databricks &amp; D365 data stay mocked;
            decisions and guardrails remain deterministic.
          </span>
        ) : (
          <span>
            <strong>Mock mode:</strong> Foundry, Databricks &amp; D365 are all
            mocked — deterministic and fully offline.
          </span>
        )}
      </div>

      <nav className="tabs">
        <button
          className={tab === "sequential" ? "tab tab-on" : "tab"}
          onClick={() => setTab("sequential")}
        >
          Sequential review
          <small>Option A · single facility</small>
        </button>
        <button
          className={tab === "multiagent" ? "tab tab-on" : "tab"}
          onClick={() => setTab("multiagent")}
        >
          Multi-agent plan
          <small>Option B · cross-facility</small>
        </button>
      </nav>

      <main>
        {tab === "sequential" ? (
          <SequentialView mode={mode} />
        ) : (
          <MultiAgentView mode={mode} />
        )}
      </main>

      <footer className="app-foot">
        <span>
          Nothing writes to D365 without an explicit human approval. Every write
          is logged with an audit id.
        </span>
      </footer>
    </div>
  );
}
