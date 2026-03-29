# Strands Agents SDK + Bedrock AgentCore 整合設計

本文件定義如何將 Strands Agents SDK 和 Amazon Bedrock 整合到壽險 AI Agent Demo 中，
以及未來部署到 Bedrock AgentCore Runtime 的路徑。

---

## 設計原則

1. **LLM 用在該用的地方** — Orchestrator 用 LLM 理解意圖和彙整結果，Worker Agent 用 deterministic logic 確保精確性
2. **Strands 原生 A2A** — 用 Strands 的 `A2AServer` / `A2AAgent` 取代手寫的 A2A 實作
3. **本地開發 = 部署結構** — 本地用 `A2AServer.serve()`，部署用 `BedrockAgentCoreApp`，agent 程式碼不變
4. **漸進式整合** — 保留 rule-based fallback，Bedrock 不可用時仍可 demo

---

## Agent 分類：LLM vs Deterministic

| Agent | 類型 | LLM 用途 | Strands 角色 |
|-------|------|---------|-------------|
| **Recommendation** | LLM-powered | 意圖解析、呼叫決策、結果彙整、對話引導 | `Agent` + `@tool`（tools 是其他 agent 的 A2A 呼叫） |
| **Product Catalog** | Deterministic | 無 | `A2AServer` 包裝純 Python tool |
| **Underwriting Risk** | Hybrid | 評分用公式，解讀用 LLM | `Agent` + `@tool`（tool 是評分公式） |
| **Premium Calculator** | Deterministic | 無 | `A2AServer` 包裝純 Python tool |
| **Compliance Check** | Deterministic | 無 | `A2AServer` 包裝純 Python tool |
| **Explanation** (新增) | LLM-powered | 解釋保險術語和條款 | `Agent`（純 LLM，無 tool） |

### 為什麼 Worker Agent 不用 LLM

- **保費計算**：必須精確到元，LLM 算數不可靠
- **合規檢查**：法規是硬規則（15 歲以下不得有死亡給付），不能讓 LLM 自由解讀
- **商品查詢**：從 JSON 篩選是確定性操作，LLM 可能幻覺出不存在的商品
- 這些 agent 的價值在於「被 Orchestrator 呼叫時提供精確資料」，不在於自主推理

### 為什麼 Orchestrator 和 Risk Agent 需要 LLM

- **Orchestrator**：理解「我剛結婚該買什麼保險」→ 推理出需要壽險+醫療險，這是 LLM 的強項
- **Risk Agent**：評分公式算出 68 分，但「你的高血壓是主要扣分因子，建議持續控制」這種解讀需要 LLM

---

## 架構總覽

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│                    A2A POST /message:stream                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Recommendation Agent (Strands Agent + Bedrock Claude)           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ system_prompt: "你是保險規劃顧問..."                        │  │
│  │ model: Bedrock Claude Sonnet                               │  │
│  │ tools:                                                     │  │
│  │   - check_compliance  → A2AAgent → Compliance Agent        │  │
│  │   - assess_risk       → A2AAgent → Risk Agent              │  │
│  │   - search_products   → A2AAgent → Product Agent           │  │
│  │   - calculate_premium → A2AAgent → Premium Agent           │  │
│  │   - explain_term      → A2AAgent → Explanation Agent       │  │
│  │                                                             │  │
│  │ LLM 自主決定：                                               │  │
│  │   1. 解析用戶意圖                                            │  │
│  │   2. 決定呼叫哪些 tool（哪些 agent）                          │  │
│  │   3. 組織回覆                                                │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ A2AServer (Strands 原生，streaming)                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ A2A SendMessage
          ┌────────────────┼────────────────┬──────────────────┐
          ▼                ▼                ▼                  ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │ Product      │ │ Risk         │ │ Premium      │ │ Compliance   │
   │ Catalog      │ │ Assessment   │ │ Calculator   │ │ Check        │
   │              │ │              │ │              │ │              │
   │ Deterministic│ │ Hybrid       │ │ Deterministic│ │ Deterministic│
   │ @tool only   │ │ Agent+@tool  │ │ @tool only   │ │ @tool only   │
   │ A2AServer    │ │ A2AServer    │ │ A2AServer    │ │ A2AServer    │
   └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
          │                                                    │
          └────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Harbor API      │
                  │  (discover,      │
                  │   policy,        │
                  │   lifecycle)     │
                  └─────────────────┘
```

---

## 各 Agent 詳細設計

### 1. Recommendation Agent（LLM-powered Orchestrator）

```python
from strands import Agent, tool
from strands.agent.a2a_agent import A2AAgent
from strands.multiagent.a2a import A2AServer

# 其他 agent 的 A2A client（URL 從 Harbor discover 取得）
compliance = A2AAgent(endpoint="http://localhost:8204")
risk = A2AAgent(endpoint="http://localhost:8202")
products = A2AAgent(endpoint="http://localhost:8201")
premium = A2AAgent(endpoint="http://localhost:8203")

@tool
def check_compliance(age: int, product_category: str) -> str:
    """檢查投保資格。回傳是否符合資格及限制說明。"""
    result = compliance(f"檢查 {age} 歲投保 {product_category}")
    return str(result.message)

@tool
def assess_risk(age: int, gender: str, height_cm: float, weight_kg: float,
                occupation_class: int, smoking_status: str,
                conditions: list[str], family_history: list[str]) -> str:
    """評估被保險人的核保風險等級。回傳風險分數、等級、各因子評分。"""
    prompt = (f"評估風險：{age}歲{gender}，{height_cm}cm {weight_kg}kg，"
              f"職業類別{occupation_class}，吸菸:{smoking_status}，"
              f"既往症:{conditions}，家族史:{family_history}")
    result = risk(prompt)
    return str(result.message)

@tool
def search_products(age: int, types: list[str], budget_monthly: int = 0) -> str:
    """搜尋適合的保險商品。回傳符合條件的國泰/富邦商品清單。"""
    prompt = f"搜尋 {age} 歲適合的 {','.join(types)}，月預算 {budget_monthly}"
    result = products(prompt)
    return str(result.message)

@tool
def calculate_premium(product_ids: list[str], age: int, risk_class: str) -> str:
    """試算保費。回傳各商品的月繳/年繳保費。"""
    prompt = f"試算 {','.join(product_ids)} 的保費，{age}歲，風險等級 {risk_class}"
    result = premium(prompt)
    return str(result.message)

orchestrator = Agent(
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    system_prompt="""你是專業的保險規劃顧問。根據客戶需求，協調多個專家完成保險規劃。

你的工作流程：
1. 理解客戶需求（年齡、預算、想要的險種）
2. 如果客戶提供了健康資訊，先做風險預評估
3. 搜尋適合的商品
4. 試算保費
5. 用清楚易懂的方式彙整結果

注意事項：
- 如果客戶沒說年齡或想要什麼險種，先追問
- 風險預評估結果僅供參考，要提醒客戶
- 比較商品時要客觀，列出各自優缺點
- 保費超出預算時主動建議調整方案""",
    tools=[check_compliance, assess_risk, search_products, calculate_premium],
)

server = A2AServer(agent=orchestrator, host="0.0.0.0", port=8200)
```

**LLM 帶來的改進：**
- 不再需要手寫 keyword matching 意圖解析 — Claude 自己理解
- 不再需要硬編碼呼叫順序 — Claude 自己決定先做什麼
- 追問邏輯自然 — Claude 知道缺什麼資訊會主動問
- 結果彙整有品質 — Claude 會組織成有邏輯的建議，不只是拼接

### 2. Product Catalog Agent（Deterministic）

```python
from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

@tool
def search_products(age: int, types: list[str], budget_monthly: int = 0,
                    providers: list[str] = ["cathay", "fubon"]) -> str:
    """搜尋保險商品。根據年齡、險種、預算篩選。回傳 JSON 格式的商品清單。"""
    # 原有的 _load_products() + _filter() 邏輯，完全不變
    ...

@tool
def compare_products(product_ids: list[str]) -> str:
    """比較指定商品的保障內容。回傳 JSON 格式的比較結果。"""
    ...

# 用最輕量的 model — 這裡 LLM 只是把 tool 結果轉發，不做推理
# 或者用 callback 模式完全跳過 LLM
agent = Agent(
    system_prompt="你是商品查詢助手。直接呼叫 tool 回傳結果，不要加入自己的解讀。",
    tools=[search_products, compare_products],
    callback_handler=None,
)

server = A2AServer(agent=agent, host="0.0.0.0", port=8201)
```

> **注意**：Deterministic agent 仍然用 Strands Agent 包裝，因為 A2AServer 需要一個 Agent 實例。
> 但 system_prompt 指示 LLM 直接呼叫 tool 不做額外推理，實際上 LLM 只是一個 pass-through。
> 如果要完全避免 LLM 呼叫（省成本），可以用 Strands 的 Custom Agent 模式直接處理。

### 3. Underwriting Risk Agent（Hybrid）

```python
@tool
def calculate_risk_score(age: int, height_cm: float, weight_kg: float,
                         occupation_class: int, smoking_status: str,
                         conditions: list[str], family_history: list[str]) -> str:
    """計算核保風險分數。回傳 JSON 格式的評分結果。"""
    # 原有的加權評分公式，完全不變
    ...

agent = Agent(
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    system_prompt="""你是核保風險評估專家。

工作流程：
1. 呼叫 calculate_risk_score tool 取得精確的風險評分
2. 根據評分結果，用專業但易懂的語言解讀：
   - 哪些因子是主要風險來源
   - 預期的核保結果（標準體/加費/拒保）
   - 改善建議（如果有的話）
3. 一定要附上免責聲明：此為預評估，非正式核保結果

重要：風險分數必須由 tool 計算，你不要自己算。你的角色是解讀結果。""",
    tools=[calculate_risk_score],
)

server = A2AServer(agent=agent, host="0.0.0.0", port=8202)
```

**Hybrid 的好處：**
- 分數精確（公式算的）
- 解讀有溫度（LLM 寫的）
- 例如：「你的 BMI 27.8 落在標準範圍，但接近次標準的邊界。建議控制體重，降到 25 以下可以升級到優良體費率。」

### 4. Explanation Agent（新增，純 LLM）

```python
agent = Agent(
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    system_prompt="""你是保險知識專家，專門用白話文解釋保險術語和條款。

規則：
- 用台灣的保險用語
- 舉生活化的例子
- 不要給投保建議，只解釋概念
- 如果不確定，說「建議諮詢保險業務員」""",
    tools=[],  # 純 LLM，不需要 tool
)

server = A2AServer(agent=agent, host="0.0.0.0", port=8205)
```

**使用場景：**
- 用戶問「什麼是實支實付？」→ Orchestrator 呼叫 Explanation Agent
- 用戶問「等待期是什麼意思？」→ 直接由 LLM 回答

---

## Bedrock 模型配置

| Agent | 模型 | 理由 |
|-------|------|------|
| Recommendation | Claude Sonnet | 需要強推理能力（意圖解析、多步驟規劃） |
| Risk Assessment | Claude Sonnet | 需要專業解讀能力 |
| Explanation | Claude Haiku | 簡單的知識問答，用便宜的模型即可 |
| Product/Premium/Compliance | 不使用 LLM | Deterministic，或用最輕量模型 pass-through |

### 成本控制

- Deterministic agent 盡量不打 Bedrock API
- Orchestrator 每次對話約 1-3 次 LLM 呼叫（意圖解析 + tool 決策 + 結果彙整）
- Risk Agent 每次評估 1 次 LLM 呼叫（解讀結果）
- Explanation Agent 每次問答 1 次 LLM 呼叫

---

## 本地開發 vs AgentCore Runtime 部署

### 本地開發模式

```
每個 agent 用 A2AServer.serve() 啟動在獨立 port：

  Recommendation:  localhost:8200  (Strands Agent + Bedrock Claude)
  Product Catalog: localhost:8201  (Strands A2AServer + deterministic tool)
  Risk Assessment: localhost:8202  (Strands Agent + Bedrock Claude)
  Premium Calc:    localhost:8203  (Strands A2AServer + deterministic tool)
  Compliance:      localhost:8204  (Strands A2AServer + deterministic tool)
  Explanation:     localhost:8205  (Strands Agent + Bedrock Claude)

前提：需要 AWS credentials 存取 Bedrock API
Fallback：Bedrock 不可用時切換到 rule-based 模式（不用 LLM）
```

### AgentCore Runtime 部署模式

```
每個 agent 包成 BedrockAgentCoreApp → Docker container → ECR → AgentCore Runtime：

  agentcore configure --entrypoint agents/recommendation.py
  agentcore launch

AgentCore 自動提供：
  - IAM role（存取 Bedrock API）
  - Serverless scaling
  - /invocations + /ping endpoint
  - ARM64 container runtime
  - CloudWatch observability
```

### 程式碼結構（支援兩種模式）

```python
# agents/product_catalog.py

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

# --- Domain Logic（不變）---
def _load_products(): ...
def _filter(products, age, types, budget): ...

# --- Strands Tool ---
@tool
def search_products(age: int, types: list[str], budget_monthly: int = 0) -> str:
    """搜尋保險商品。"""
    products = _load_products()
    return json.dumps(_filter(products, age, types, budget), ensure_ascii=False)

# --- Strands Agent ---
agent = Agent(
    system_prompt="直接呼叫 tool 回傳結果。",
    tools=[search_products],
    callback_handler=None,
)

# --- A2A Server（本地開發用）---
def serve_local():
    server = A2AServer(agent=agent, host="0.0.0.0", port=8201)
    server.serve()

# --- AgentCore entrypoint（部署用）---
def create_agentcore_app():
    from bedrock_agentcore.runtime import BedrockAgentCoreApp
    app = BedrockAgentCoreApp()

    @app.entrypoint
    async def invoke(payload):
        result = agent(payload.get("prompt", ""))
        return {"result": result.message}

    return app

if __name__ == "__main__":
    serve_local()
```

---

## Harbor 整合

### Agent 註冊時的 runtime 資訊

本地開發：
```bash
harbor register product-catalog-agent "商品目錄 Agent" \
  --capabilities product_search,product_comparison \
  --provider on-prem \
  --protocol a2a \
  --endpoint http://localhost:8201
```

AgentCore 部署後：
```bash
harbor register product-catalog-agent "商品目錄 Agent" \
  --capabilities product_search,product_comparison \
  --provider aws \
  --runtime bedrock-agentcore \
  --resource-id arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/product-catalog \
  --protocol a2a
```

### Orchestrator 的 agent 發現流程

```python
# 1. 從 Harbor discover 取得 agent URL
url = await harbor.discover("product_search")
# 本地: "http://localhost:8201"
# AgentCore: "https://xxx.bedrock-agentcore.us-west-2.amazonaws.com"

# 2. 用 Strands A2AAgent 呼叫
agent = A2AAgent(endpoint=url)
result = agent("搜尋 35 歲適合的醫療險")
```

---

## 專案結構更新

```
samples/life-insurance/
├── backend/
│   ├── agents/
│   │   ├── recommendation.py     # Strands Agent + Bedrock Claude + A2AServer
│   │   ├── product_catalog.py    # Strands A2AServer + deterministic @tool
│   │   ├── underwriting_risk.py  # Strands Agent + Bedrock Claude + A2AServer
│   │   ├── premium_calculator.py # Strands A2AServer + deterministic @tool
│   │   ├── compliance_check.py   # Strands A2AServer + deterministic @tool
│   │   └── explanation.py        # Strands Agent + Bedrock Claude (新增)
│   ├── tools/                    # 純 Python domain logic（@tool 包裝前的函式）
│   │   ├── product_search.py     # _load_products(), _filter()
│   │   ├── risk_scoring.py       # _assess(), 加權評分公式
│   │   ├── premium_calc.py       # _calc_one(), 費率表
│   │   └── compliance_rules.py   # _check(), 法規規則
│   ├── harbor_client.py          # Harbor API client
│   ├── config.py                 # 模型選擇、port 配置、fallback 開關
│   └── main.py                   # 啟動所有 agent（本地開發用）
├── infrastructure/               # CDK IaC（新增）
│   ├── bin/
│   │   └── app.ts                # CDK app entry
│   ├── lib/
│   │   ├── config.ts             # Agent 定義與環境配置
│   │   ├── insurance-demo-stack.ts # 主 stack（ECR + IAM + 6 AgentCore Runtime）
│   │   └── constructs/
│   │       └── agent-runtime.ts  # 可重用的 AgentCore Runtime L3 construct
│   ├── package.json
│   ├── tsconfig.json
│   └── cdk.json
├── deploy/                       # Docker 打包（新增）
│   ├── Dockerfile                # ARM64 container（共用 base + build arg）
│   └── requirements.txt          # strands-agents[a2a], bedrock-agentcore
├── data/                         # 模擬資料（不變）
├── frontend/                     # React Chat UI（不變）
├── scripts/
│   ├── seed_harbor.sh            # 本地模式：註冊 agent 到 Harbor
│   ├── seed_harbor_agentcore.sh  # AgentCore 模式：用 ARN 註冊（新增）
│   ├── build_images.sh           # 打包 6 個 agent image（新增）
│   ├── run_local.sh              # 本地啟動（A2AServer 模式）
│   └── deploy_agentcore.sh       # 一鍵部署（build + cdk deploy + seed）
├── requirement.md
├── architecture.md
├── api-contract.md
└── strands-integration.md
```

---

## Fallback 策略

```python
# config.py
import os

USE_BEDROCK = os.getenv("USE_BEDROCK", "true").lower() == "true"
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0")
BEDROCK_MODEL_LIGHT = os.getenv("BEDROCK_MODEL_LIGHT", "us.anthropic.claude-haiku-3-20250620-v1:0")
```

```python
# agents/recommendation.py
from config import USE_BEDROCK, BEDROCK_MODEL

if USE_BEDROCK:
    orchestrator = Agent(
        model=BEDROCK_MODEL,
        system_prompt="你是保險規劃顧問...",
        tools=[check_compliance, assess_risk, search_products, calculate_premium],
    )
else:
    # Fallback: 用原有的 keyword matching + rule-based 邏輯
    # 不呼叫 Bedrock API，適合離線 demo 或成本控制
    orchestrator = RuleBasedOrchestrator(...)
```

---

## 開發里程碑更新

### Phase 1：資料與 Domain Logic ✅ 已完成
### Phase 2：Harbor 整合（待做）
### Phase 3：Chat Web App ✅ 已完成

### Phase 4：Strands + Bedrock 整合（新增）

- [ ] 安裝 `strands-agents[a2a]` 和 `bedrock-agentcore`
- [ ] 抽取 domain logic 到 `tools/` 目錄
- [ ] 改造 Recommendation Agent → Strands Agent + Bedrock Claude
- [ ] 改造 Risk Agent → Strands Agent (hybrid)
- [ ] 新增 Explanation Agent
- [ ] 改造 3 個 Deterministic Agent → Strands A2AServer
- [ ] 實作 fallback 模式（USE_BEDROCK=false）
- [ ] 端到端測試（本地 A2AServer 模式）

## AgentCore Runtime 部署（CDK IaC）

每個 agent 獨立部署到 AgentCore Runtime，用 CDK 管理所有基礎設施。

### 部署架構

```
┌─────────────────────────────────────────────────────────────────┐
│  AWS Account                                                     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  ECR Repository: harbor-insurance-demo                       │ │
│  │  Tags: recommendation, product-catalog, underwriting-risk,   │ │
│  │        premium-calculator, compliance-check, explanation      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ AgentCore    │ │ AgentCore    │ │ AgentCore    │             │
│  │ Runtime      │ │ Runtime      │ │ Runtime      │             │
│  │              │ │              │ │              │             │
│  │ recommendation│ │ product-    │ │ underwriting-│             │
│  │ -agent       │ │ catalog     │ │ risk         │             │
│  │              │ │              │ │              │             │
│  │ Protocol:A2A │ │ Protocol:A2A│ │ Protocol:A2A │             │
│  │ LLM: Sonnet  │ │ LLM: none  │ │ LLM: Sonnet  │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ AgentCore    │ │ AgentCore    │ │ AgentCore    │             │
│  │ Runtime      │ │ Runtime      │ │ Runtime      │             │
│  │              │ │              │ │              │             │
│  │ premium-     │ │ compliance-  │ │ explanation  │             │
│  │ calculator   │ │ check        │ │              │             │
│  │              │ │              │ │              │             │
│  │ Protocol:A2A │ │ Protocol:A2A│ │ Protocol:A2A │             │
│  │ LLM: none    │ │ LLM: none  │ │ LLM: Haiku   │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  IAM Role: InsuranceDemoAgentRole                            │ │
│  │  - bedrock:InvokeModel (Claude Sonnet, Haiku)                │ │
│  │  - ecr:GetDownloadUrlForLayer, BatchGetImage                 │ │
│  │  - logs:CreateLogGroup, PutLogEvents                         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Harbor Central (主專案的 CDK stack)                          │ │
│  │  - 6 個 agent 註冊在 Harbor registry                         │ │
│  │  - endpoint 指向各 AgentCore Runtime ARN                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### CDK 專案結構

```
samples/life-insurance/infrastructure/
├── bin/
│   └── app.ts                    # CDK app entry
├── lib/
│   ├── config.ts                 # Agent 定義與環境配置
│   ├── insurance-demo-stack.ts   # 主 stack
│   └── constructs/
│       └── agent-runtime.ts      # 可重用的 AgentCore Runtime construct
├── package.json
├── tsconfig.json
└── cdk.json
```

### Agent 定義（config.ts）

```typescript
export interface AgentConfig {
  name: string;
  description: string;
  ecrTag: string;
  protocol: 'A2A' | 'HTTP' | 'MCP';
  usesLlm: boolean;
  envVars?: Record<string, string>;
}

export const AGENTS: AgentConfig[] = [
  {
    name: 'recommendation',
    description: '保險規劃推薦引擎 (Orchestrator)',
    ecrTag: 'recommendation',
    protocol: 'A2A',
    usesLlm: true,
    envVars: { BEDROCK_MODEL: 'us.anthropic.claude-sonnet-4-20250514-v1:0' },
  },
  {
    name: 'product_catalog',
    description: '壽險商品目錄查詢',
    ecrTag: 'product-catalog',
    protocol: 'A2A',
    usesLlm: false,
  },
  {
    name: 'underwriting_risk',
    description: '核保風險預評估',
    ecrTag: 'underwriting-risk',
    protocol: 'A2A',
    usesLlm: true,
    envVars: { BEDROCK_MODEL: 'us.anthropic.claude-sonnet-4-20250514-v1:0' },
  },
  {
    name: 'premium_calculator',
    description: '保費試算',
    ecrTag: 'premium-calculator',
    protocol: 'A2A',
    usesLlm: false,
  },
  {
    name: 'compliance_check',
    description: '投保資格合規檢查',
    ecrTag: 'compliance-check',
    protocol: 'A2A',
    usesLlm: false,
  },
  {
    name: 'explanation',
    description: '保險知識解釋',
    ecrTag: 'explanation',
    protocol: 'A2A',
    usesLlm: true,
    envVars: { BEDROCK_MODEL: 'us.anthropic.claude-haiku-3-20250620-v1:0' },
  },
];
```

### AgentCore Runtime Construct（agent-runtime.ts）

```typescript
// 可重用的 L3 construct — 一個 agent = 一個 AgentCore Runtime
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { CfnRuntime } from 'aws-cdk-lib/aws-bedrockagentcore';
import { Construct } from 'constructs';

export interface AgentRuntimeProps {
  agentName: string;
  description: string;
  ecrImageUri: string;
  role: iam.IRole;
  protocol: 'A2A' | 'HTTP' | 'MCP';
  environmentVariables?: Record<string, string>;
}

export class AgentRuntime extends Construct {
  public readonly runtime: CfnRuntime;
  public readonly runtimeArn: string;

  constructor(scope: Construct, id: string, props: AgentRuntimeProps) {
    super(scope, id);

    this.runtime = new CfnRuntime(this, 'Runtime', {
      agentRuntimeName: `insurance-demo-${props.agentName}`,
      description: props.description,
      agentRuntimeArtifact: {
        containerConfiguration: {
          containerUri: props.ecrImageUri,
        },
      },
      networkConfiguration: {
        networkMode: 'PUBLIC',
      },
      protocolConfiguration: props.protocol,
      roleArn: props.role.roleArn,
      environmentVariables: props.environmentVariables,
      tags: {
        Project: 'harbor-insurance-demo',
        Agent: props.agentName,
      },
    });

    this.runtimeArn = this.runtime.attrAgentRuntimeArn;
  }
}
```

### 主 Stack（insurance-demo-stack.ts）

```typescript
import * as cdk from 'aws-cdk-lib';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { AGENTS } from './config';
import { AgentRuntime } from './constructs/agent-runtime';

export class InsuranceDemoStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // --- ECR Repository (shared, one tag per agent) ---
    const repo = new ecr.Repository(this, 'AgentRepo', {
      repositoryName: 'harbor-insurance-demo',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      emptyOnDelete: true,
    });

    // --- IAM Role (shared by all agents) ---
    const agentRole = new iam.Role(this, 'AgentRole', {
      roleName: 'InsuranceDemoAgentRole',
      assumedBy: new iam.ServicePrincipal('bedrock-agentcore.amazonaws.com'),
    });

    // Bedrock model access
    agentRole.addToPolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
      resources: ['arn:aws:bedrock:*::foundation-model/*'],
    }));

    // ECR pull
    repo.grantPull(agentRole);

    // CloudWatch logs
    agentRole.addToPolicy(new iam.PolicyStatement({
      actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
      resources: ['*'],
    }));

    // --- AgentCore Runtimes (one per agent) ---
    const runtimes: Record<string, AgentRuntime> = {};

    for (const agent of AGENTS) {
      const imageUri = `${repo.repositoryUri}:${agent.ecrTag}`;

      runtimes[agent.name] = new AgentRuntime(this, `Agent-${agent.name}`, {
        agentName: agent.name.replace(/_/g, '-'),
        description: agent.description,
        ecrImageUri: imageUri,
        role: agentRole,
        protocol: agent.protocol,
        environmentVariables: agent.envVars,
      });
    }

    // --- Outputs ---
    new cdk.CfnOutput(this, 'EcrRepoUri', { value: repo.repositoryUri });

    for (const [name, rt] of Object.entries(runtimes)) {
      new cdk.CfnOutput(this, `${name}-arn`, {
        value: rt.runtimeArn,
        description: `AgentCore Runtime ARN for ${name}`,
      });
    }
  }
}
```

### 部署流程

```bash
# 1. Build & push all agent images
cd samples/life-insurance
./scripts/build_images.sh   # 每個 agent 打包成 ARM64 container

# 2. Deploy infrastructure
cd infrastructure
npm install
npx cdk deploy

# 3. 取得 AgentCore Runtime ARN
# CDK output 會列出每個 agent 的 ARN

# 4. 註冊到 Harbor（用 AgentCore endpoint）
./scripts/seed_harbor_agentcore.sh
```

### Docker 打包策略

每個 agent 共用一個 base image，用 build arg 指定 entrypoint：

```dockerfile
# deploy/Dockerfile
FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY backend/ ./backend/
COPY data/ ./data/

ARG AGENT_MODULE=agents.recommendation
ENV AGENT_MODULE=${AGENT_MODULE}

EXPOSE 8080
CMD ["uv", "run", "python", "-m", "backend.${AGENT_MODULE}"]
```

Build script：
```bash
# scripts/build_images.sh
REPO="123456789012.dkr.ecr.us-west-2.amazonaws.com/harbor-insurance-demo"

for agent in recommendation product-catalog underwriting-risk premium-calculator compliance-check explanation; do
  module=$(echo $agent | tr '-' '_')
  docker buildx build --platform linux/arm64 \
    --build-arg AGENT_MODULE=agents.${module} \
    -t ${REPO}:${agent} --push .
done
```

### Phase 5：AgentCore Runtime 部署（已完成）

#### Dockerfile（實際版本）

```dockerfile
FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY deploy/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY backend/ ./backend/
COPY data/ ./data/
COPY deploy/entrypoint.py ./entrypoint.py

ENV USE_BEDROCK=true

EXPOSE 9000
CMD ["python", "entrypoint.py"]
```

**關鍵要點：**
- **Port 9000**：AgentCore A2A protocol 要求 container listen 在 port 9000（不是 8080，8080 是 HTTP protocol 用的）
- **ARM64**：AgentCore Runtime 要求 ARM64 container
- **entrypoint.py**：專用的 AgentCore entrypoint，直接 import domain tools（不透過 A2A 呼叫其他 agent）

#### entrypoint.py（Orchestrator agent）

```python
from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

# 直接 import domain tools
from backend.tools.product_search import search
from backend.tools.risk_scoring import assess
from backend.tools.premium_calc import calc_batch
from backend.tools.compliance_rules import check

# 定義 @tool wrappers...

agent = Agent(
    model=BEDROCK_MODEL,
    system_prompt=SYSTEM_PROMPT,
    tools=[check_compliance, assess_risk, search_products, calculate_premium],
)

# A2AServer on port 9000 — AgentCore Runtime A2A protocol
server = A2AServer(agent=agent, host="0.0.0.0", port=9000)
server.serve()
```

#### IAM 權限（重要）

AgentCore Runtime 的 IAM role 需要同時包含 `foundation-model/*` 和 `inference-profile/*` 的 resource：

```typescript
agentRole.addToPolicy(new iam.PolicyStatement({
  actions: ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
  resources: [
    "arn:aws:bedrock:*::foundation-model/*",
    `arn:aws:bedrock:*:${this.account}:inference-profile/*`,
  ],
}));
```

> Cross-region inference profile（如 `us.anthropic.claude-sonnet-4-20250514-v1:0`）的 ARN 格式是 `inference-profile/*`，不是 `foundation-model/*`。缺少此權限會導致 container 內的 Strands agent 呼叫 Bedrock model 時回傳 `NoCredentialsError`，AgentCore Runtime 回傳 424 (Failed Dependency)。

#### CDK 部署

```bash
# 1. 建立 ECR repo 並推送 images
aws ecr create-repository --repository-name harbor-insurance-demo
./scripts/build_images.sh

# 2. 部署 AgentCore Runtime（CDK 會建立 IAM role + 6 個 Runtime）
cd infrastructure && npx cdk deploy

# 3. 註冊 agents 到 Harbor
./scripts/seed_harbor_agentcore.sh
```

#### Agent Proxy（Harbor → AgentCore Runtime）

Harbor 的 CDK stack 包含一個 Agent Proxy Lambda，用於將前端的請求轉發到 AgentCore Runtime：

```
Frontend → CloudFront → API Gateway → Agent Proxy Lambda → AgentCore Runtime (A2A)
```

- Lambda 將 user prompt 包裝成 A2A JSON-RPC `message/send` 格式
- 透過 `InvokeAgentRuntime` API 呼叫 AgentCore Runtime
- 5 分鐘 timeout，避免 API Gateway 的 29s hard limit
- 需要 `bedrock-agentcore:InvokeAgentRuntime` IAM 權限
