# Harbor Insurance Demo

壽險 AI Agent 協作平台 — 展示 Harbor + A2A + Strands Agents + Bedrock AgentCore 的完整整合。

## Demo 展示

### 1. Harbor Agent Registry — 統一管理跨雲 Agent

6 個 AI Agent 全部註冊到 Harbor，透過 `harbor list` 一覽所有 agent 的生命週期狀態：

```
$ harbor list
  explanation-agent              published    保險知識 Agent
  recommendation-agent           published    推薦引擎 Agent
  compliance-check-agent         published    合規檢查 Agent
  premium-calculator-agent       published    保費試算 Agent
  underwriting-risk-agent        published    風險預評估 Agent
  product-catalog-agent          published    商品目錄 Agent
```

每個 agent 都有完整的 metadata，包含 runtime、endpoint、capabilities：

```
$ harbor status recommendation-agent
Agent:      推薦引擎 Agent (recommendation-agent)
Lifecycle:  published
Visibility: org_wide
Version:    1.0.0
Caps:       plan_recommendation, needs_analysis
Updated:    2026-03-29T11:25:15.693772Z
```

### 2. Harbor Discover — 按能力動態發現 Agent

不需要硬編碼 agent 的 URL。透過 `harbor discover` 按 capability 查詢，Harbor 只回傳 **published** 狀態的 agent：

```
$ harbor discover -c risk_assessment
  underwriting-risk-agent        風險預評估 Agent

$ harbor discover -c product_search
  product-catalog-agent          商品目錄 Agent

$ harbor discover -c premium_calculation
  premium-calculator-agent       保費試算 Agent
```

### 3. Harbor Lifecycle — 緊急停用 Agent

`suspended` 是緊急停用開關。被停用的 agent 立即從 discover 結果中消失：

```
$ harbor lifecycle underwriting-risk-agent suspended --reason 'incident-1234'
✓ underwriting-risk-agent → suspended

$ harbor list
  underwriting-risk-agent        suspended    風險預評估 Agent
  explanation-agent              published    保險知識 Agent
  ...

$ harbor discover -c risk_assessment
(empty — suspended agent is no longer discoverable!)

$ harbor lifecycle underwriting-risk-agent published
✓ underwriting-risk-agent → published
```

### 4. A2A Agent 互動 — 完整保險規劃

透過 AgentCore Runtime 的 A2A protocol 呼叫 Orchestrator Agent。Agent 自動協調多個專家 agent（商品搜尋、保費試算、風險評估），產出完整的保險規劃建議：

```
>>> Invoking Orchestrator Agent via A2A protocol on AgentCore Runtime...
>>> Prompt: 我30歲，月預算3000元，想買醫療險，請幫我搜尋商品並試算保費

<<< Agent Response (26.0s):

## 搜尋結果與保費試算

根據您的需求（30歲，月預算3000元，醫療險），我為您找到2款符合預算的商品：

### 方案一：國泰真全意住院醫療險 ⭐推薦
- **月保費：833元**
- 住院日額：2,000元 / 手術限額：20萬元
- 實支實付型，無等待期

### 方案二：富邦人生自由行醫療險
- **月保費：977元**
- 住院日額：2,500元 / 手術限額：25萬元
- 實支實付型，較高的手術限額

### 風險評估結果
您的核保風險等級為「優體」，兩款商品都有15%的折扣。

### 建議
1. 國泰真全意住院醫療險較符合您的預算，月保費833元
2. 您還可以考慮用剩餘預算搭配重大傷病險或癌症險
```

### 5. Harbor Frontend — Agent 狀態監控

部署在 CloudFront 上的 React SPA，即時顯示所有 agent 的狀態：

![Harbor Insurance Demo Frontend](docs/images/harbor-frontend-dashboard.png)

---

## 架構

```
┌─────────────────────────────────────────────────────────────────┐
│                    Harbor Central (AWS Serverless)               │
│  CloudFront + WAF → API Gateway → Lambda (FastAPI) → DynamoDB  │
│                                                                  │
│  Registry │ Discovery │ Lifecycle │ Policy │ Audit │ Health     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              register / discover / heartbeat
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│              AgentCore Runtime (6 × A2A Agents)                  │
│                                                                  │
│  ┌─────────────┐  A2A   ┌──────────────┐  A2A  ┌────────────┐ │
│  │ Orchestrator ├───────►│Product Catalog├──────►│  Premium   │ │
│  │ (Claude)     │        │              │       │ Calculator │ │
│  └──────┬───────┘        └──────────────┘       └────────────┘ │
│         │ A2A                                                    │
│  ┌──────┴───────┐  ┌──────────────┐  ┌─────────────────┐      │
│  │ Underwriting │  │  Compliance  │  │   Explanation    │      │
│  │ Risk (Claude)│  │    Check     │  │   (Claude Haiku) │      │
│  └──────────────┘  └──────────────┘  └─────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

6 個 AI Agent 透過 A2A v1.0 協議通訊，由 Harbor 管理生命週期：

| Agent | 類型 | Protocol | LLM | Capabilities |
|-------|------|----------|-----|--------------|
| Recommendation | Orchestrator | A2A | Claude Sonnet | plan_recommendation, needs_analysis |
| Product Catalog | Deterministic | A2A | — | product_search, product_comparison |
| Underwriting Risk | Hybrid | A2A | Claude Sonnet | risk_assessment, risk_scoring |
| Premium Calculator | Deterministic | A2A | — | premium_calculation, quote_generation |
| Compliance Check | Deterministic | A2A | — | kyc_check, regulatory_compliance |
| Explanation | LLM-powered | A2A | Claude Haiku | term_explanation, faq |

## Quick Start（本地開發）

```bash
# 1. 安裝 Python 依賴
pip install 'strands-agents[a2a]'

# 2. 啟動所有 agent
cd backend
python main.py

# 3. 安裝並啟動前端
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## 部署到 AWS

### Step 1: 部署 Harbor Central

```bash
cd ../../infrastructure
npm install
npx cdk deploy
```

### Step 2: Build & Push Agent Images

```bash
cd ../samples/life-insurance
REPO="<account>.dkr.ecr.<region>.amazonaws.com/harbor-insurance-demo"
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com

docker buildx build --platform linux/arm64 -t "${REPO}:recommendation" -f deploy/Dockerfile --push .
# ... repeat for other agents
```

### Step 3: 部署 AgentCore Runtime

```bash
cd infrastructure
npx cdk deploy
```

### Step 4: 註冊 Agent 到 Harbor

```bash
export HARBOR_URL="https://<api-id>.execute-api.<region>.amazonaws.com/api/v1"
export HARBOR_TENANT="dev-tenant-000000000000"
export HARBOR_OWNER="dev@harbor.local"

harbor register recommendation-agent "推薦引擎 Agent" \
  --capabilities plan_recommendation,needs_analysis \
  --provider aws --runtime bedrock-agentcore --protocol a2a \
  --resource-id "arn:aws:bedrock-agentcore:..." \
  --endpoint "arn:aws:bedrock-agentcore:..." \
  --visibility org_wide

# ... repeat for other agents, then publish:
harbor lifecycle recommendation-agent submitted
harbor lifecycle recommendation-agent in_review
harbor lifecycle recommendation-agent approved
harbor lifecycle recommendation-agent published
```

### Step 5: 部署 Frontend

```bash
cd frontend
npm run build
aws s3 sync dist/ "s3://<frontend-bucket>/" --delete
aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
```

## 文件

- [requirement.md](./requirement.md) — 業務需求與使用情境
- [architecture.md](./architecture.md) — 架構規範
- [api-contract.md](./api-contract.md) — A2A API Contract
- [strands-integration.md](./strands-integration.md) — Strands + Bedrock + AgentCore 整合設計
