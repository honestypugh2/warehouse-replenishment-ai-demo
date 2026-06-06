#!/bin/bash
# Start script for the AI Warehouse Replenishment Orchestration Demo.
# Launches the FastAPI backend (8080) and the React/Vite frontend (5173).
#
# Modes:
#   ./start.sh           Mock mode — Foundry, Databricks & D365 all mocked (offline).
#   ./start.sh --live    Live Foundry — real Azure AI model reasoning; data,
#                        Databricks & D365 stay mocked. Requires AZURE_FOUNDRY_*
#                        in .env and `az login`.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# Mode selection: --live flag overrides; otherwise honor FOUNDRY_MODE / default mock.
FOUNDRY_MODE="${FOUNDRY_MODE:-mock}"
for arg in "$@"; do
    case "$arg" in
        --live) FOUNDRY_MODE="live" ;;
        --mock) FOUNDRY_MODE="mock" ;;
        *) echo "Unknown option: $arg (use --live or --mock)"; exit 1 ;;
    esac
done

# In live mode, load the azd environment outputs (Foundry endpoint, App Insights
# connection string, FOUNDRY_USE_AGENTS) so persistent agents + tracing light up.
# These are produced by `azd provision` and written to .azure/<env>/.env.
if [ "$FOUNDRY_MODE" = "live" ]; then
    AZD_ENV_FILE=""
    if command -v azd >/dev/null 2>&1; then
        AZD_ENV_NAME="$(azd env list --output json 2>/dev/null \
            | grep -o '"Name": *"[^"]*"' | head -n1 | sed 's/.*"Name": *"\([^"]*\)".*/\1/')"
        [ -n "$AZD_ENV_NAME" ] && AZD_ENV_FILE="$PROJECT_ROOT/.azure/$AZD_ENV_NAME/.env"
    fi
    # Fallback: first .azure/*/.env we can find.
    if [ -z "$AZD_ENV_FILE" ] || [ ! -f "$AZD_ENV_FILE" ]; then
        AZD_ENV_FILE="$(ls "$PROJECT_ROOT"/.azure/*/.env 2>/dev/null | head -n1)"
    fi
    if [ -n "${AZD_ENV_FILE:-}" ] && [ -f "$AZD_ENV_FILE" ]; then
        echo "Loading live Foundry config from: $AZD_ENV_FILE"
        set -a
        # shellcheck disable=SC1090
        . "$AZD_ENV_FILE"
        set +a
    else
        echo "Warning: no .azure/<env>/.env found. Run 'azd provision' first;"
        echo "         live mode will fall back to chat/mock without agents or traces."
    fi
    # Persistent agents are required for them to appear in the Foundry portal.
    export FOUNDRY_USE_AGENTS="${FOUNDRY_USE_AGENTS:-true}"
fi

echo "========================================"
echo "Replenishment Demo Application Launcher"
echo "Foundry mode: $FOUNDRY_MODE"
echo "========================================"

# Check if the Python virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "Error: Virtual environment not found at $PROJECT_ROOT/.venv"
    echo "Create it with: uv sync"
    exit 1
fi

# Stop any existing services first
fuser -k 8080/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true
sleep 1

# Install frontend dependencies if needed
if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    (cd "$PROJECT_ROOT/frontend" && npm install) > "$LOG_DIR/frontend-install.log" 2>&1
fi

# Start backend
echo "Starting Backend API..."
cd "$PROJECT_ROOT"
MOCK_MODE="${MOCK_MODE:-true}" FOUNDRY_MODE="$FOUNDRY_MODE" \
    FOUNDRY_USE_AGENTS="${FOUNDRY_USE_AGENTS:-false}" \
    AZURE_FOUNDRY_PROJECT_ENDPOINT="${AZURE_FOUNDRY_PROJECT_ENDPOINT:-}" \
    APPLICATIONINSIGHTS_CONNECTION_STRING="${APPLICATIONINSIGHTS_CONNECTION_STRING:-}" \
    "$PROJECT_ROOT/.venv/bin/uvicorn" app.main:app \
    --app-dir src --host 0.0.0.0 --port 8080 --reload \
    > "$LOG_DIR/backend.log" 2>&1 &
echo "Backend started (PID: $!)"

sleep 3

# Start frontend
echo "Starting Frontend App..."
cd "$PROJECT_ROOT/frontend"
npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
echo "Frontend started (PID: $!)"

sleep 3

echo ""
echo "========================================"
echo "Services started! (Foundry mode: $FOUNDRY_MODE)"
echo "========================================"
echo ""
echo "Backend:  http://localhost:8080"
echo "API Docs: http://localhost:8080/docs"
echo "Frontend: http://localhost:5173"
echo ""
echo "View logs:"
echo "  tail -f $LOG_DIR/backend.log"
echo "  tail -f $LOG_DIR/frontend.log"
echo ""
echo "Stop: ./stop.sh"
