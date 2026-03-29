#!/bin/bash
# Build and push all agent Docker images to ECR.
# Usage: ./scripts/build_images.sh <ecr-repo-uri>
# Example: ./scripts/build_images.sh 123456789012.dkr.ecr.us-west-2.amazonaws.com/harbor-insurance-demo

set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO=${1:?Usage: $0 <ecr-repo-uri>}
REGION=${AWS_REGION:-us-west-2}

echo "=== Logging in to ECR ==="
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${REPO%%/*}"

AGENTS="recommendation product_catalog underwriting_risk premium_calculator compliance_check explanation"

for agent in $AGENTS; do
  tag=$(echo "$agent" | tr '_' '-')
  echo ""
  echo "=== Building ${tag} ==="
  docker buildx build --platform linux/arm64 \
    --build-arg AGENT_MODULE="$agent" \
    -t "${REPO}:${tag}" \
    -f "$DIR/deploy/Dockerfile" \
    --push \
    "$DIR"
done

echo ""
echo "=== All images pushed ==="
