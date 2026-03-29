#!/bin/bash
# One-click deploy: build images + CDK deploy + register to Harbor.
# Usage: ./scripts/deploy_agentcore.sh

set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Step 1: Deploy CDK infrastructure ==="
cd "$DIR/infrastructure"
npm install
npx cdk deploy --require-approval never --outputs-file cdk-outputs.json

# Extract ECR repo URI from outputs
ECR_REPO=$(python3 -c "import json; d=json.load(open('cdk-outputs.json')); print(d['InsuranceDemoStack']['EcrRepoUri'])")
echo "ECR Repo: $ECR_REPO"

echo ""
echo "=== Step 2: Build and push agent images ==="
cd "$DIR"
./scripts/build_images.sh "$ECR_REPO"

echo ""
echo "=== Step 3: Register agents to Harbor ==="
./scripts/seed_harbor_agentcore.sh

echo ""
echo "=== Deployment complete! ==="
