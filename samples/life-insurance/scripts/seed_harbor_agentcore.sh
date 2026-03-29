#!/bin/bash
# Post-deploy: read CDK outputs, generate manifest, register agents in Harbor.
# Usage: ./scripts/seed_harbor_agentcore.sh [--stack InsuranceDemoStack]
#
# Reads AgentCore Runtime ARNs from CloudFormation outputs,
# generates a JSON manifest, then calls `harbor deploy-register`.

set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
STACK=${1:-InsuranceDemoStack}
REGION=${AWS_REGION:-us-west-2}

export HARBOR_URL=${HARBOR_URL:-http://localhost:8100/api/v1}
export HARBOR_TENANT=${HARBOR_TENANT:-demo-tenant}
export HARBOR_OWNER=${HARBOR_OWNER:-cdk-deploy@harbor.local}

echo "=== Reading CDK outputs from stack: $STACK ==="
OUTPUTS=$(aws cloudformation describe-stacks \
  --stack-name "$STACK" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs' \
  --output json 2>/dev/null || echo "[]")

get_arn() {
  echo "$OUTPUTS" | python3 -c "
import sys, json
outputs = json.load(sys.stdin)
key = '$1'
for o in outputs:
    if key in o['OutputKey']:
        print(o['OutputValue'])
        break
else:
    print('NOT_FOUND')
"
}

RECOMMENDATION_ARN=$(get_arn "recommendation-arn")
PRODUCT_ARN=$(get_arn "product-catalog-arn")
RISK_ARN=$(get_arn "underwriting-risk-arn")
PREMIUM_ARN=$(get_arn "premium-calculator-arn")
COMPLIANCE_ARN=$(get_arn "compliance-check-arn")
EXPLANATION_ARN=$(get_arn "explanation-arn")

echo "=== Generating manifest ==="
MANIFEST="$DIR/scripts/.agent-manifest.json"

cat > "$MANIFEST" <<EOF
[
  {
    "agent_id": "recommendation-agent",
    "name": "推薦引擎 Agent",
    "description": "根據客戶需求協調多個 Agent 產出完整保險規劃建議",
    "tenant_id": "${HARBOR_TENANT}",
    "owner": {"owner_id": "${HARBOR_OWNER}", "team": "insurance-demo", "org_id": "harbor"},
    "capabilities": ["plan_recommendation", "needs_analysis"],
    "runtime": {"provider": "aws", "runtime": "bedrock-agentcore", "resource_id": "${RECOMMENDATION_ARN}"},
    "endpoint": {"url": "${RECOMMENDATION_ARN}", "protocol": "a2a"},
    "visibility": "org_wide"
  },
  {
    "agent_id": "product-catalog-agent",
    "name": "商品目錄 Agent",
    "description": "查詢國泰/富邦壽險商品目錄",
    "tenant_id": "${HARBOR_TENANT}",
    "owner": {"owner_id": "${HARBOR_OWNER}", "team": "insurance-demo", "org_id": "harbor"},
    "capabilities": ["product_search", "product_comparison"],
    "runtime": {"provider": "aws", "runtime": "bedrock-agentcore", "resource_id": "${PRODUCT_ARN}"},
    "endpoint": {"url": "${PRODUCT_ARN}", "protocol": "a2a"},
    "visibility": "org_wide"
  },
  {
    "agent_id": "underwriting-risk-agent",
    "name": "風險預評估 Agent",
    "description": "根據被保險人資料做核保風險預評估",
    "tenant_id": "${HARBOR_TENANT}",
    "owner": {"owner_id": "${HARBOR_OWNER}", "team": "insurance-demo", "org_id": "harbor"},
    "capabilities": ["risk_assessment", "risk_scoring"],
    "runtime": {"provider": "aws", "runtime": "bedrock-agentcore", "resource_id": "${RISK_ARN}"},
    "endpoint": {"url": "${RISK_ARN}", "protocol": "a2a"},
    "visibility": "org_wide"
  },
  {
    "agent_id": "premium-calculator-agent",
    "name": "保費試算 Agent",
    "description": "根據商品與風險等級試算保費",
    "tenant_id": "${HARBOR_TENANT}",
    "owner": {"owner_id": "${HARBOR_OWNER}", "team": "insurance-demo", "org_id": "harbor"},
    "capabilities": ["premium_calculation", "quote_generation"],
    "runtime": {"provider": "aws", "runtime": "bedrock-agentcore", "resource_id": "${PREMIUM_ARN}"},
    "endpoint": {"url": "${PREMIUM_ARN}", "protocol": "a2a"},
    "visibility": "org_wide"
  },
  {
    "agent_id": "compliance-check-agent",
    "name": "合規檢查 Agent",
    "description": "檢查投保資格與法規限制",
    "tenant_id": "${HARBOR_TENANT}",
    "owner": {"owner_id": "${HARBOR_OWNER}", "team": "insurance-demo", "org_id": "harbor"},
    "capabilities": ["kyc_check", "regulatory_compliance"],
    "runtime": {"provider": "aws", "runtime": "bedrock-agentcore", "resource_id": "${COMPLIANCE_ARN}"},
    "endpoint": {"url": "${COMPLIANCE_ARN}", "protocol": "a2a"},
    "visibility": "org_wide"
  },
  {
    "agent_id": "explanation-agent",
    "name": "保險知識 Agent",
    "description": "用白話文解釋保險術語和條款",
    "tenant_id": "${HARBOR_TENANT}",
    "owner": {"owner_id": "${HARBOR_OWNER}", "team": "insurance-demo", "org_id": "harbor"},
    "capabilities": ["term_explanation", "faq"],
    "runtime": {"provider": "aws", "runtime": "bedrock-agentcore", "resource_id": "${EXPLANATION_ARN}"},
    "endpoint": {"url": "${EXPLANATION_ARN}", "protocol": "a2a"},
    "visibility": "org_wide"
  }
]
EOF

echo "=== Registering agents in Harbor ==="
harbor deploy-register "$MANIFEST" --publish

rm -f "$MANIFEST"
echo ""
echo "=== Verifying ==="
harbor list
