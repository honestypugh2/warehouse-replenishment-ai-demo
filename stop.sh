#!/bin/bash
# Stop script for the AI Warehouse Replenishment Orchestration Demo.

echo "Stopping Replenishment Demo Application..."

# Kill backend on port 8080
fuser -k 8080/tcp 2>/dev/null || true
echo "Backend stopped"

# Kill frontend on port 5173
fuser -k 5173/tcp 2>/dev/null || true
echo "Frontend stopped"

echo "All services stopped!"
