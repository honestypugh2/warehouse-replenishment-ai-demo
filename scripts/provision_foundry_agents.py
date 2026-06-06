#!/usr/bin/env python
"""Provision the demo's persistent Foundry agents.

Creates (or updates) the warehouse-replenishment agents in the configured
Foundry project so they appear in the portal **Agents** list and can be invoked
at runtime when ``FOUNDRY_USE_AGENTS=true``.

Prerequisites:
  * ``AZURE_FOUNDRY_PROJECT_ENDPOINT`` set (azd writes it to .azure/<env>/.env)
  * Signed in with ``az login`` (DefaultAzureCredential), Foundry User role
  * Production deps installed:  uv pip install -r requirements-prod.txt

Usage:
  python scripts/provision_foundry_agents.py          # create/update agents
  python scripts/provision_foundry_agents.py --list   # list current agents
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from foundry.agents.foundry_agent_service import (  # noqa: E402
    AGENT_SPECS,
    FoundryAgentError,
    _project_client,
    provision_agents,
)


def _list() -> int:
    client = _project_client()
    agents = list(client.agents.list())
    if not agents:
        print("No agents found in the project.")
        return 0
    print(f"{len(agents)} agent(s) in the project:")
    for agent in agents:
        latest = getattr(getattr(agent, "versions", None), "latest", None)
        version = getattr(latest, "version", "?") if latest else "?"
        print(f"  - {agent.name:24s} (latest version: {version})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List current agents and exit.")
    args = parser.parse_args()

    try:
        if args.list:
            return _list()

        print(f"Provisioning {len(AGENT_SPECS)} Foundry agent(s)...")
        names = provision_agents()
        for role, agent_name in names.items():
            print(f"  ✓ {role:12s} -> {agent_name}")
        print("\nDone. Set FOUNDRY_USE_AGENTS=true to route live narration "
              "through the persistent recommender agent.")
        return 0
    except FoundryAgentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
