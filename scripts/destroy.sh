#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INFRA_DIR="$SCRIPT_DIR/../infrastructure"
PROFILE="${AWS_PROFILE:-default}"

echo "🚢 Harbor — Destroy"
echo "  Profile: $PROFILE"
echo ""

cd "$INFRA_DIR"
JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 npx cdk destroy --force --profile "$PROFILE" "$@"

echo ""
echo "✅ Destroy complete"
