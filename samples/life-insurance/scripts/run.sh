#!/bin/bash
# Start all services for the insurance demo.
# Usage: ./scripts/run.sh

set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Starting Insurance Demo ==="
echo ""

# 1. Start individual agent servers in background
echo "Starting agents..."
cd "$DIR/backend"

python -m uvicorn main:app_product_catalog --port 8201 --host 0.0.0.0 &
python -m uvicorn main:app_underwriting_risk --port 8202 --host 0.0.0.0 &
python -m uvicorn main:app_premium_calculator --port 8203 --host 0.0.0.0 &
python -m uvicorn main:app_compliance_check --port 8204 --host 0.0.0.0 &
sleep 1
python -m uvicorn main:app_recommendation --port 8200 --host 0.0.0.0 &

echo ""
echo "Agents started:"
echo "  Recommendation (Orchestrator): http://localhost:8200"
echo "  Product Catalog:               http://localhost:8201"
echo "  Underwriting Risk:             http://localhost:8202"
echo "  Premium Calculator:            http://localhost:8203"
echo "  Compliance Check:              http://localhost:8204"
echo ""

# 2. Start frontend
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
wait
