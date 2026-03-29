#!/bin/bash
# Start all services locally for the insurance demo.
# Usage: ./scripts/run_local.sh

set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Harbor Insurance Demo (Local Mode) ==="
echo ""

# Start all agents via main.py
cd "$DIR/backend"
echo "Starting 6 agents..."
python main.py &
BACKEND_PID=$!
sleep 8

echo ""
echo "Agents started:"
echo "  Recommendation (Orchestrator): http://localhost:8200"
echo "  Product Catalog:               http://localhost:8201"
echo "  Underwriting Risk:             http://localhost:8202"
echo "  Premium Calculator:            http://localhost:8203"
echo "  Compliance Check:              http://localhost:8204"
echo "  Explanation:                    http://localhost:8205"
echo ""

# Start frontend
if [ -d "$DIR/frontend/node_modules" ]; then
  echo "Starting frontend..."
  cd "$DIR/frontend"
  npm run dev &
  echo "  Frontend: http://localhost:5173"
else
  echo "Frontend not installed. Run: cd frontend && npm install && npm run dev"
fi

echo ""
echo "Press Ctrl+C to stop all services."
trap "kill $BACKEND_PID 2>/dev/null; kill $(jobs -p) 2>/dev/null" EXIT
wait
