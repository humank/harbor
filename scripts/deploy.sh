#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INFRA_DIR="$SCRIPT_DIR/../infrastructure"
PROFILE="${AWS_PROFILE:-default}"

echo "🚢 Harbor — Deploy"
echo "  Profile: $PROFILE"
echo "  Region:  ${AWS_REGION:-us-east-1}"
echo ""

cd "$INFRA_DIR"
npm install --silent
JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 npx cdk deploy --require-approval broadening --profile "$PROFILE" "$@"

echo ""
echo "✅ Deploy complete"
