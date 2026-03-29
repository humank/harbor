# 壽險 AI Agent Demo — 架構規範

本文件定義 `samples/life-insurance/` 的開發架構約束。
所有程式碼必須遵循這些規範。

---

## 設計原則

1. **這是 demo，不是 production** — 優先可讀性與展示效果，不需要過度工程化
2. **A2A-native** — Agent 間通訊完全遵循 A2A v1.0 HTTP+JSON binding（`POST /message:send`、`POST /message:stream`）
3. **每個 Agent 是獨立的 A2A Server** — 提供 `/.well-known/agent-card.json`，接受 A2A `SendMessageRequest`
4. **Orchestrator 是 A2A Client + A2A Server** — 對前端是 Server（接受 streaming），對其他 agent 是 Client（發送 SendMessage）
5. **Harbor 是 agent 發現與治理層** — orchestrator 透過 Harbor discover 取得 agent 的 A2A endpoint，不硬編碼
6. **結構化資料用 A2A Part.data** — 風險評估、商品比較等結果透過 `Part.data` + `mediaType: application/json` 傳遞
7. **完整 API contract 見 [api-contract.md](./api-contract.md)** — 包含所有 Agent Card、通訊範例、Pydantic model

---

## Backend 分層架構

```
┌─────────────────────────────────────────────┐
│  Layer 5: A2A Server (Strands A2AServer)     │
│  - 自動處理 A2A protocol (JSON-RPC)          │
│  - 自動生成 Agent Card                       │
├─────────────────────────────────────────────┤
│  Layer 4: Strands Agent                      │
│  - system_prompt 定義角色                     │
│  - model 指定 Bedrock Claude（LLM agent 才有）│
│  - tools 掛載 Layer 3 的 @tool               │
├─────────────────────────────────────────────┤
│  Layer 3: Strands @tool                      │
│  - 包裝 domain logic 為 LLM 可呼叫的 tool    │
│  - 定義參數型別和 docstring                   │
├─────────────────────────────────────────────┤
│  Layer 2: Domain Logic (tools/)              │
│  - 純 Python 函式，無框架依賴                 │
│  - 商品查詢、風險評分、保費計算、合規檢查      │
│  - 可獨立單元測試                             │
├─────────────────────────────────────────────┤
│  Layer 1: Data (data/)                       │
│  - 靜態 JSON 檔案                             │
│  - 商品資料、職業類別表                        │
├─────────────────────────────────────────────┤
│  Harbor Client + A2A Client                  │
│  - Harbor: discover / policy check           │
│  - A2A: Strands A2AAgent 呼叫其他 agent       │
└─────────────────────────────────────────────┘
```

### 規則

1. **Domain logic 在 `tools/` 目錄**，純 Python 函式，不依賴 Strands 或 FastAPI。
2. **`agents/` 目錄的每個檔案**是一個完整的 agent：Strands Agent + A2AServer。
3. **LLM-powered agent**（Recommendation, Risk, Explanation）使用 Bedrock Claude，LLM 負責推理和彙整。
4. **Deterministic agent**（Product, Premium, Compliance）不呼叫 LLM，tool 結果直接回傳。
5. **Fallback 模式**：`USE_BEDROCK=false` 時所有 agent 退化為 rule-based，不打 Bedrock API。
6. **Strands + Bedrock 整合的完整設計見 [strands-integration.md](./strands-integration.md)**。

---

## 部署模式

### 本地開發

每個 agent 是獨立的 A2A Server，使用 Strands `A2AServer` 在不同 port 上啟動：

| Agent | Port |
|-------|------|
| Recommendation (Orchestrator) | 8200 |
| Product Catalog | 8201 |
| Underwriting Risk | 8202 |
| Premium Calculator | 8203 |
| Compliance Check | 8204 |
| Explanation | 8205 |

### AgentCore Runtime 部署

部署到 AWS Bedrock AgentCore Runtime 時：

- **Protocol**: A2A（JSON-RPC 2.0 over HTTP）
- **Port**: 9000（AgentCore A2A protocol 要求 container listen 在 port 9000）
- **Platform**: ARM64 container
- **Health check**: `GET /ping` 回傳 `{"status": "Healthy", "time_of_last_update": <unix_timestamp>}`
- **Agent Card**: `GET /.well-known/agent-card.json`
- **A2A endpoint**: `POST /`（JSON-RPC `message/send`）

Orchestrator agent 使用專用的 `deploy/entrypoint.py`，直接 import domain tools（不透過 A2A 呼叫其他 agent），因為在 AgentCore Runtime 上所有 tools 都嵌入同一個 container。

### IAM 權限

AgentCore Runtime 的 IAM role 需要：

| Permission | Resource | Purpose |
|------------|----------|---------|
| `bedrock:InvokeModel` | `arn:aws:bedrock:*::foundation-model/*` | Foundation model access |
| `bedrock:InvokeModelWithResponseStream` | `arn:aws:bedrock:*::foundation-model/*` | Streaming model access |
| `bedrock:InvokeModel` | `arn:aws:bedrock:*:*:inference-profile/*` | Cross-region inference profile access |
| `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer` | ECR repo ARN | Pull container images |
| `ecr:GetAuthorizationToken` | `*` | ECR auth |
| `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` | `*` | CloudWatch logs |

> **重要**: Cross-region inference profile（如 `us.anthropic.claude-sonnet-4-20250514-v1:0`）的 ARN 格式是 `inference-profile/*`，不是 `foundation-model/*`。IAM policy 必須同時包含兩者。

---

## Agent 模組結構

每個 agent 是一個獨立的 A2A Server，遵循統一結構：

```python
# agents/product_catalog.py

from fastapi import APIRouter
from models import SendMessageRequest, StreamResponse, Task, Message, Part, Artifact

router = APIRouter()

# --- Agent Card ---

AGENT_CARD = { ... }  # 見 api-contract.md

@router.get("/.well-known/agent-card.json")
async def agent_card():
    return AGENT_CARD

# --- A2A endpoint ---

@router.post("/message:send")
async def send_message(req: SendMessageRequest):
    """A2A SendMessage — 接收查詢，回傳 Task + Artifact"""
    data_part = _extract_data_part(req.message.parts)
    skill = data_part.get("skill", "product-search")

    if skill == "product-search":
        products = _search_products(data_part)
        return _make_task_response(req.message.context_id, "products-result", products)
    elif skill == "product-compare":
        comparison = _compare_products(data_part)
        return _make_task_response(req.message.context_id, "comparison-result", comparison)

# --- 內部邏輯（純函式，可測試）---

def _search_products(params: dict) -> dict: ...
def _compare_products(params: dict) -> dict: ...
def _extract_data_part(parts: list[Part]) -> dict: ...
def _make_task_response(context_id, artifact_name, data) -> dict: ...
```

### 規則

- 每個 agent 提供 `/.well-known/agent-card.json` 和 `POST /message:send`
- Orchestrator 額外提供 `POST /message:stream`（SSE）
- 業務邏輯寫成 private function（`_` prefix），方便單元測試
- A2A 的 request/response 格式處理集中在 endpoint 函式
- 結構化資料放在 `Part.data`，文字放在 `Part.text`

---

## Orchestrator 設計

recommendation-agent 同時是 A2A Server（對前端）和 A2A Client（對其他 agent）：

```python
# agents/recommendation.py

async def stream_message(req: SendMessageRequest) -> AsyncGenerator[str, None]:
    """A2A SendStreamingMessage — 接收用戶訊息，stream 回 A2A events"""

    context_id = req.message.context_id or str(uuid4())
    task_id = str(uuid4())

    # 1. 回傳初始 Task（WORKING）
    yield _sse_data(StreamResponse(task=Task(
        id=task_id, contextId=context_id,
        status=TaskStatus(state="TASK_STATE_WORKING",
            message=Message(role="ROLE_AGENT", parts=[Part(text="收到！開始規劃...")]))
    )))

    # 2. 解析意圖
    intent = parse_intent(req.message, history)

    # 3. 透過 Harbor 發現 agent
    agents = await harbor.discover(intent.required_capabilities)

    # 4. 依序呼叫 agent（A2A SendMessage），每步 yield status update
    if intent.needs_compliance:
        yield _sse_status(task_id, context_id, "正在檢查投保資格...")
        result = await a2a_client.send_message(agents["compliance"].url, compliance_msg)
        yield _sse_status(task_id, context_id, "✅ 投保資格確認通過")

    if intent.needs_risk:
        yield _sse_status(task_id, context_id, "正在評估風險...")
        risk_task = await a2a_client.send_message(agents["risk"].url, risk_msg)
        # 將下游 agent 的 Artifact 轉發給前端
        yield _sse_artifact(task_id, context_id, risk_task.artifacts[0])

    # ... 其他 agent

    # 5. 完成
    yield _sse_status(task_id, context_id, "以上是推薦方案，需要調整嗎？",
                      state="TASK_STATE_COMPLETED")
```

### 規則

- Orchestrator 不包含商品查詢、風險計算等業務邏輯
- 呼叫其他 agent 使用 A2A `POST /message:send`，不是直接函式呼叫
- 下游 agent 回傳的 Artifact 直接轉發（或合併）給前端
- 多輪對話透過 A2A 的 `contextId` + `taskId` 管理
- 缺少資訊時回傳 `TASK_STATE_INPUT_REQUIRED`

---

## Harbor Client 封裝

```python
# harbor_client.py — 唯一碰 Harbor API 的地方

class HarborClient:
    def __init__(self, base_url: str, tenant: str):
        self.base_url = base_url
        self.tenant = tenant

    async def discover(self, capability: str) -> AgentRecord | None:
        """透過 Harbor 發現 agent，取得 A2A endpoint URL"""
        ...

    async def check_policy(self, from_agent: str, to_agent: str) -> PolicyDecision:
        """檢查通訊權限"""
        ...

    async def get_agent_status(self, agent_id: str) -> str:
        """查詢 agent lifecycle 狀態"""
        ...
```

### 規則

- 用 `httpx.AsyncClient` 呼叫 Harbor API
- 所有方法回傳 Pydantic model，不回傳 raw dict
- Harbor 連線失敗時 graceful fallback（demo 可以 fallback 到本地直接呼叫）

---

## A2A Client 封裝

Orchestrator 用這個 client 呼叫其他 agent 的 A2A endpoint：

```python
# a2a_client.py — A2A HTTP+JSON binding client

class A2AClient:
    async def send_message(self, agent_url: str, message: Message) -> Task | Message:
        """A2A SendMessage — POST {agent_url}/message:send"""
        ...

    async def get_agent_card(self, agent_url: str) -> dict:
        """取得 agent 的 Agent Card"""
        # GET {agent_url}/.well-known/agent-card.json
        ...
```

### 規則

- 用 `httpx.AsyncClient` 呼叫 A2A endpoint
- Request/Response 遵循 A2A HTTP+JSON binding 格式
- 帶 `A2A-Version: 1.0` header
- 回傳的 Task 或 Message 解析為 Pydantic model

---

## Models 設計

所有資料模型集中在 `models.py`：

```python
# models.py — 所有 agent 共用的型別

# --- Chat ---
class ChatMessage(BaseModel): ...       # 用戶/助理訊息
class SSEEvent(BaseModel): ...          # SSE 事件

# --- Product Catalog ---
class Product(BaseModel): ...           # 商品資料
class ProductSearchRequest(BaseModel): ...
class ProductSearchResponse(BaseModel): ...

# --- Underwriting Risk ---
class RiskInput(BaseModel): ...         # 被保險人資料
class RiskFactor(BaseModel): ...        # 單一因子評分
class RiskAssessment(BaseModel): ...    # 完整評估結果

# --- Premium ---
class PremiumRequest(BaseModel): ...
class PremiumResult(BaseModel): ...

# --- Compliance ---
class ComplianceRequest(BaseModel): ...
class ComplianceResult(BaseModel): ...

# --- Recommendation ---
class Intent(BaseModel): ...            # 解析後的用戶意圖
class Recommendation(BaseModel): ...    # 最終推薦方案
```

### 規則

- 所有 model 都是 Pydantic `BaseModel`
- Model 只定義資料結構，不含邏輯
- Enum 值用 lowercase string
- 可選欄位用 `Field(default=...)` 或 `| None`

---

## Frontend 架構

```
┌─────────────────────────────────────────────┐
│  App.tsx                                     │
│  - 主 layout（左右分欄）                      │
│  - 管理全域狀態（agent status）               │
├──────────────────┬──────────────────────────┤
│  AgentPanel      │  ChatWindow               │
│  - agent 狀態列表 │  - 訊息列表               │
│  - 協作流程圖     │  - 輸入框                 │
│                  │  - SSE 連線管理            │
├──────────────────┴──────────────────────────┤
│  Message Components                          │
│  - MessageBubble (text)                      │
│  - RiskCard (risk_card)                      │
│  - ProductCard (product_comparison)          │
│  - PremiumTable (premium_summary)            │
│  - AgentStatus (agent_status)                │
└─────────────────────────────────────────────┘
```

### 規則

- **React 18+ functional components only**，不用 class component
- **TypeScript strict mode**，不用 `any`
- **Tailwind CSS** 搭配 ui-ux-pro-max 設計系統 token，不用 CSS modules
- **狀態管理**：`useState` / `useReducer`，不用 Redux
- **SSE 連線**：封裝在 `useChat` hook 中，用 `EventSource` API
- **訊息渲染**：根據 `message.type` 分派到對應的 card component
- **一個 component 一個檔案**，檔名 = component 名（PascalCase）
- **設計系統**：實作前先執行 `ui-ux-pro-max --design-system --persist --page chat` 產生 page-level token

### 訊息分派邏輯

前端解析 A2A `StreamResponse`，根據事件類型分派：

```tsx
// hooks/useChat.ts — 解析 SSE data
function handleSSEData(raw: string) {
  const event: StreamResponse = JSON.parse(raw);

  if (event.task) {
    // 初始 Task — 更新 task 狀態
    updateTask(event.task);
    if (event.task.status.message) renderStatusMessage(event.task.status.message);
  }
  if (event.statusUpdate) {
    // 狀態更新 — 渲染為聊天氣泡
    updateTaskStatus(event.statusUpdate);
    if (event.statusUpdate.status.message) renderStatusMessage(event.statusUpdate.status.message);
  }
  if (event.artifactUpdate) {
    // Artifact — 根據 data 結構分派到 Rich Card
    renderArtifact(event.artifactUpdate.artifact);
  }
}

// components/ArtifactRenderer.tsx — 根據 artifact 內容分派
function ArtifactRenderer({ artifact }: { artifact: Artifact }) {
  const dataPart = artifact.parts.find(p => p.data);
  if (!dataPart?.data) return <TextBubble parts={artifact.parts} />;

  const data = dataPart.data;
  if ("score" in data && "risk_class" in data)  return <RiskCard data={data} />;
  if ("products" in data)                        return <ProductCard data={data} />;
  if ("total_monthly" in data)                   return <PremiumTable data={data} />;
  if ("eligible" in data)                        return <ComplianceStatus data={data} />;
  return <JsonView data={data} />;
}
```

---

## 錯誤處理

| 層級 | 策略 |
|------|------|
| Agent endpoint | 回傳結構化錯誤 `{"error": "message"}`，HTTP 4xx/5xx |
| Orchestrator | catch agent 錯誤 → yield 錯誤事件給前端，不中斷整個流程 |
| Harbor Client | 連線失敗 → log warning + fallback 到本地呼叫 |
| Frontend | SSE 斷線 → 自動重連 + 顯示「重新連線中...」 |

### 規則

- Agent 失敗不應該讓整個對話崩潰 — orchestrator 跳過失敗的 agent，告知用戶
- 前端永遠顯示有意義的錯誤訊息，不顯示 stack trace

---

## 測試策略

| 層級 | 測試方式 |
|------|---------|
| Agent 邏輯 | 單元測試 — 直接呼叫 `_filter_products()`、`_calculate_risk()` 等 private function |
| Agent endpoint | 用 `TestClient` 打 API，驗證 request/response 格式 |
| Orchestrator | Mock 其他 agent 的回應，驗證協調流程和 SSE 事件順序 |
| Harbor 整合 | Mock Harbor API，驗證 discover / policy check 流程 |
| Frontend | 手動測試為主（demo 專案不強制前端自動化測試） |

---

## 與 Harbor 主專案的差異

| 面向 | Harbor 主專案 | Sample Project |
|------|-------------|----------------|
| Agent 通訊 | Harbor 自定義 API | A2A v1.0 HTTP+JSON binding |
| Agent 發現 | Harbor registry API | Harbor discover → A2A Agent Card |
| 分層 | API → Service → Store → DynamoDB（三層嚴格分離） | Agent 模組自包含（A2A endpoint + 邏輯 + 資料） |
| 持久化 | DynamoDB single-table | 靜態 JSON + in-memory |
| DI | Constructor injection + FastAPI Depends | 簡單 import，不需要 DI container |
| 錯誤處理 | Domain exception → HTTP mapping | A2A error codes（TaskNotFound 等） |
| 測試 | moto mock + 完整覆蓋 | 單元測試為主，不強制覆蓋率 |
| Auth | Cognito JWT + RBAC | 無（demo 不需要認證） |
| Streaming | 自定義 SSE | A2A StreamResponse（Task + StatusUpdate + ArtifactUpdate） |

> 這些簡化是刻意的 — sample project 的目的是展示 Harbor + A2A 的整合，不是展示企業級架構。
> 但 agent 間通訊完全符合 A2A v1.0，這是核心賣點。
