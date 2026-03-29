#!/bin/bash
# Register all agents to Harbor for local development.
# Requires: Harbor running on localhost:8100

set -e

export HARBOR_URL=${HARBOR_URL:-http://localhost:8100/api/v1}
export HARBOR_TENANT=${HARBOR_TENANT:-demo-tenant}
export HARBOR_OWNER=${HARBOR_OWNER:-dev@harbor.local}

echo "=== Registering agents to Harbor (local mode) ==="

harbor register product-catalog-agent "商品目錄 Agent" \
  --desc "查詢國泰/富邦壽險商品目錄" \
  --capabilities product_search,product_comparison \
  --provider on-prem --protocol a2a \
  --endpoint http://localhost:8201 \
  --visibility org_wide

harbor register underwriting-risk-agent "風險預評估 Agent" \
  --desc "根據被保險人資料做核保風險預評估" \
  --capabilities risk_assessment,risk_scoring \
  --provider on-prem --protocol a2a \
  --endpoint http://localhost:8202 \
  --visibility org_wide

harbor register premium-calculator-agent "保費試算 Agent" \
  --desc "根據商品與風險等級試算保費" \
  --capabilities premium_calculation,quote_generation \
  --provider on-prem --protocol a2a \
  --endpoint http://localhost:8203 \
  --visibility org_wide

harbor register compliance-check-agent "合規檢查 Agent" \
  --desc "檢查投保資格與法規限制" \
  --capabilities kyc_check,regulatory_compliance \
  --provider on-prem --protocol a2a \
  --endpoint http://localhost:8204 \
  --visibility org_wide

harbor register recommendation-agent "推薦引擎 Agent" \
  --desc "協調多個 Agent 產出完整保險規劃建議" \
  --capabilities plan_recommendation,needs_analysis \
  --provider on-prem --protocol a2a \
  --endpoint http://localhost:8200 \
  --visibility org_wide

harbor register explanation-agent "保險知識 Agent" \
  --desc "用白話文解釋保險術語和條款" \
  --capabilities term_explanation,faq \
  --provider on-prem --protocol a2a \
  --endpoint http://localhost:8205 \
  --visibility org_wide

echo ""
echo "=== Publishing agents (dev auto-approve) ==="
for agent in product-catalog-agent underwriting-risk-agent premium-calculator-agent compliance-check-agent recommendation-agent explanation-agent; do
  harbor lifecycle "$agent" submitted
done

echo ""
echo "=== Verifying ==="
harbor list
echo ""
echo "Done! All agents registered and published."
