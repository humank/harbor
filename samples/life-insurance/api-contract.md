# 壽險 AI Agent Demo — API Contract（A2A v1.0 Native）

所有 agent 間通訊完全遵循 [A2A Protocol v1.0](https://a2a-protocol.org/latest/specification/)。
本文件定義每個 agent 的 Agent Card、通訊格式、以及前端 ↔ Backend 的 API。

---

## 設計決策

1. **A2A-native** — Agent 間通訊使用 A2A 的 `SendMessage` / `Task` / `Part` 模型，不自定義信封格式
2. **HTTP+JSON binding** — 使用 A2A 的 REST binding（`POST /message:send`、`POST /message:stream`）
3. **結構化資料用 `Part.data`** — 風險評估、商品比較等結構化結果透過 A2A 的 `data` Part 傳遞
4. **Streaming 用 A2A `StreamResponse`** — SSE 事件格式完全符合 A2A spec
5. **Agent Card 作為發現機制** — 每個 agent 提供 `/.well-known/agent-card.json`，Harbor 同步此資訊

---

## A2A 核心概念對應

| A2A 概念 | 在本專案的對應 |
|----------|-------------|
| **Agent Card** | 每個 agent 的能力描述，Harbor 同步儲存 |
| **Message** | Client（orchestrator）與 Server（各 agent）之間的一次通訊 |
| **Task** | 一次 agent 呼叫的工作單元，有 lifecycle（submitted → working → completed） |
| **Part** | Message 或 Artifact 中的內容單元（text / data / file） |
| **Artifact** | Agent 產出的結果（風險評估報告、商品清單等） |
| **contextId** | 同一次對話的所有 Task 共用同一個 contextId |
| **Streaming** | `POST /message:stream` 回傳 SSE，包含 TaskStatusUpdate 和 ArtifactUpdate |

---

## Agent Cards

每個 agent 在 `/.well-known/agent-card.json` 提供 Agent Card。
Harbor 透過 `/agents/import-a2a` 同步這些 Agent Card。

### 1. Product Catalog Agent

```json
{
  "name": "商品目錄 Agent",
  "description": "查詢國泰/富邦壽險商品目錄，依客戶需求篩選推薦與比較",
  "version": "1.0.0",
  "supportedInterfaces": [
    {
      "url": "http://localhost:8201",
      "protocolBinding": "HTTP+JSON",
      "protocolVersion": "1.0"
    }
  ],
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "defaultInputModes": ["application/json", "text/plain"],
  "defaultOutputModes": ["application/json"],
  "skills": [
    {
      "id": "product-search",
      "name": "商品搜尋",
      "description": "依年齡、險種、預算搜尋適合的保險商品",
      "tags": ["product", "search", "insurance"],
      "examples": [
        "搜尋適合 35 歲的醫療險，月預算 5000 元",
        "列出所有重大傷病險商品"
      ],
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    },
    {
      "id": "product-compare",
      "name": "商品比較",
      "description": "比較指定商品的保障內容與保費",
      "tags": ["product", "comparison"],
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    }
  ]
}
```

### 2. Underwriting Risk Agent

```json
{
  "name": "風險預評估 Agent",
  "description": "根據被保險人健康、職業、生活習慣評估核保風險等級",
  "version": "1.0.0",
  "supportedInterfaces": [
    {
      "url": "http://localhost:8202",
      "protocolBinding": "HTTP+JSON",
      "protocolVersion": "1.0"
    }
  ],
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "defaultInputModes": ["application/json"],
  "defaultOutputModes": ["application/json"],
  "skills": [
    {
      "id": "risk-assess",
      "name": "風險預評估",
      "description": "根據被保險人資料進行核保風險預評估，回傳風險等級與各因子評分",
      "tags": ["risk", "underwriting", "assessment"],
      "examples": [
        "評估 42 歲男性，BMI 27.8，高血壓藥物控制中"
      ]
    }
  ]
}
```

### 3. Premium Calculator Agent

```json
{
  "name": "保費試算 Agent",
  "description": "根據商品、年齡、風險等級計算保費",
  "version": "1.0.0",
  "supportedInterfaces": [
    {
      "url": "http://localhost:8203",
      "protocolBinding": "HTTP+JSON",
      "protocolVersion": "1.0"
    }
  ],
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "defaultInputModes": ["application/json"],
  "defaultOutputModes": ["application/json"],
  "skills": [
    {
      "id": "premium-calc",
      "name": "保費試算",
      "description": "單一或批次試算保費",
      "tags": ["premium", "calculation", "quote"]
    }
  ]
}
```

### 4. Compliance Check Agent

```json
{
  "name": "合規檢查 Agent",
  "description": "檢查年齡、保額、財力等投保資格限制",
  "version": "1.0.0",
  "supportedInterfaces": [
    {
      "url": "http://localhost:8204",
      "protocolBinding": "HTTP+JSON",
      "protocolVersion": "1.0"
    }
  ],
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "defaultInputModes": ["application/json"],
  "defaultOutputModes": ["application/json"],
  "skills": [
    {
      "id": "compliance-verify",
      "name": "投保資格檢查",
      "description": "檢查投保資格與法規限制",
      "tags": ["compliance", "kyc", "eligibility"]
    }
  ]
}
```

### 5. Recommendation Agent（Orchestrator）

```json
{
  "name": "推薦引擎 Agent",
  "description": "根據客戶需求協調多個 Agent 產出完整保險規劃建議",
  "version": "1.0.0",
  "supportedInterfaces": [
    {
      "url": "http://localhost:8200",
      "protocolBinding": "HTTP+JSON",
      "protocolVersion": "1.0"
    }
  ],
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "defaultInputModes": ["text/plain", "application/json"],
  "defaultOutputModes": ["text/plain", "application/json"],
  "skills": [
    {
      "id": "insurance-planning",
      "name": "保險規劃",
      "description": "根據客戶需求協調多個 Agent 產出完整保險規劃建議，支援多輪對話",
      "tags": ["recommendation", "planning", "orchestrator"],
      "examples": [
        "我 35 歲男性，想買醫療險，預算月繳 5000",
        "幫我做完整的保險規劃，預算年繳 6 萬"
      ]
    }
  ]
}
```

---

## Agent 間通訊格式（A2A HTTP+JSON Binding）

所有 agent 間通訊使用 A2A 的 HTTP+JSON REST binding。

### 基本流程

Orchestrator（A2A Client）呼叫其他 agent（A2A Server）：

```
POST http://localhost:8201/message:send
Content-Type: application/json
A2A-Version: 1.0

{
  "message": {
    "messageId": "msg-uuid",
    "role": "ROLE_USER",
    "contextId": "conversation-uuid",
    "parts": [ ... ]
  }
}
```

Agent 回傳 `Task`（含 Artifact）或直接回傳 `Message`：

```json
{
  "task": {
    "id": "task-uuid",
    "contextId": "conversation-uuid",
    "status": { "state": "TASK_STATE_COMPLETED" },
    "artifacts": [
      {
        "artifactId": "artifact-uuid",
        "name": "搜尋結果",
        "parts": [
          { "data": { ... }, "mediaType": "application/json" }
        ]
      }
    ]
  }
}
```

### Part 類型使用規範

| 用途 | Part 類型 | mediaType |
|------|----------|-----------|
| 自然語言文字 | `text` | (不需要) |
| 結構化查詢條件 | `data` | `application/json` |
| 結構化結果（商品、風險評估等） | `data` | `application/json` |
| 免責聲明等附加文字 | `text` | (不需要) |

---

## 各 Agent 的 A2A 通訊範例

### 1. Product Catalog Agent

#### 商品搜尋

**Request（Orchestrator → Product Catalog）：**

```json
{
  "message": {
    "messageId": "msg-001",
    "role": "ROLE_USER",
    "contextId": "conv-abc",
    "parts": [
      {
        "data": {
          "skill": "product-search",
          "age": 35,
          "gender": "male",
          "types": ["醫療險", "重大傷病"],
          "budget_monthly": 5000,
          "providers": ["cathay", "fubon"]
        },
        "mediaType": "application/json"
      }
    ]
  }
}
```

**Response：**

```json
{
  "task": {
    "id": "task-ps-001",
    "contextId": "conv-abc",
    "status": { "state": "TASK_STATE_COMPLETED" },
    "artifacts": [
      {
        "artifactId": "products-result",
        "name": "商品搜尋結果",
        "parts": [
          {
            "data": {
              "products": [
                {
                  "product_id": "cathay-medical-001",
                  "provider": "cathay",
                  "name": "國泰真全意住院醫療險",
                  "category": "醫療險",
                  "sub_type": "實支實付",
                  "age_range": { "min": 0, "max": 70 },
                  "coverage": {
                    "daily_ward": 2000,
                    "surgery_limit": 200000,
                    "outpatient_surgery": true,
                    "emergency": true
                  },
                  "base_premium_monthly": 980,
                  "highlights": ["實支實付", "門診手術", "無等待期"],
                  "exclusions": ["既往症前30日", "美容手術"]
                },
                {
                  "product_id": "fubon-medical-001",
                  "provider": "fubon",
                  "name": "富邦人生自由行醫療險",
                  "category": "醫療險",
                  "sub_type": "實支實付",
                  "age_range": { "min": 0, "max": 65 },
                  "coverage": {
                    "daily_ward": 2500,
                    "surgery_limit": 250000,
                    "outpatient_surgery": true,
                    "emergency": true
                  },
                  "base_premium_monthly": 1150,
                  "highlights": ["高額手術限額", "門診手術"],
                  "exclusions": ["既往症前30日"]
                }
              ],
              "total": 2
            },
            "mediaType": "application/json"
          }
        ]
      }
    ]
  }
}
```

### 2. Underwriting Risk Agent

#### 風險預評估

**Request：**

```json
{
  "message": {
    "messageId": "msg-002",
    "role": "ROLE_USER",
    "contextId": "conv-abc",
    "parts": [
      {
        "data": {
          "skill": "risk-assess",
          "age": 42,
          "gender": "male",
          "height_cm": 175,
          "weight_kg": 85,
          "occupation_class": 1,
          "smoking_status": "never",
          "conditions": ["hypertension_controlled"],
          "family_history": ["none"]
        },
        "mediaType": "application/json"
      }
    ]
  }
}
```

**Response：**

```json
{
  "task": {
    "id": "task-ra-001",
    "contextId": "conv-abc",
    "status": { "state": "TASK_STATE_COMPLETED" },
    "artifacts": [
      {
        "artifactId": "risk-assessment",
        "name": "風險預評估報告",
        "parts": [
          {
            "data": {
              "score": 68,
              "risk_class": "standard_plus",
              "bmi": 27.8,
              "factors": [
                { "name": "age", "score": 70, "weight": 0.20, "level": "medium", "detail": "36-50歲，中風險" },
                { "name": "bmi", "score": 75, "weight": 0.20, "level": "standard", "detail": "BMI 27.8，標準範圍" },
                { "name": "occupation", "score": 95, "weight": 0.15, "level": "low", "detail": "第1類，低風險" },
                { "name": "smoking", "score": 100, "weight": 0.15, "level": "excellent", "detail": "非吸菸者" },
                { "name": "conditions", "score": 40, "weight": 0.20, "level": "substandard", "detail": "高血壓（藥物控制中）" },
                { "name": "family_history", "score": 100, "weight": 0.10, "level": "excellent", "detail": "無相關家族病史" }
              ],
              "prediction": "可正常承保，高血壓部分可能加費 10-25%",
              "premium_impact": "+10~25%"
            },
            "mediaType": "application/json"
          },
          {
            "text": "⚠️ 此為模擬預評估，非正式核保結果。實際核保以保險公司審核為準。"
          }
        ]
      }
    ]
  }
}
```

### 3. Premium Calculator Agent

#### 批次保費試算

**Request：**

```json
{
  "message": {
    "messageId": "msg-003",
    "role": "ROLE_USER",
    "contextId": "conv-abc",
    "parts": [
      {
        "data": {
          "skill": "premium-calc",
          "items": [
            { "product_id": "cathay-medical-001", "age": 35, "gender": "male", "risk_class": "preferred", "payment_term_years": 20 },
            { "product_id": "cathay-ci-001", "age": 35, "gender": "male", "sum_insured": 1000000, "risk_class": "preferred", "payment_term_years": 20 }
          ]
        },
        "mediaType": "application/json"
      }
    ]
  }
}
```

**Response：**

```json
{
  "task": {
    "id": "task-pc-001",
    "contextId": "conv-abc",
    "status": { "state": "TASK_STATE_COMPLETED" },
    "artifacts": [
      {
        "artifactId": "premium-result",
        "name": "保費試算結果",
        "parts": [
          {
            "data": {
              "results": [
                {
                  "product_id": "cathay-medical-001",
                  "product_name": "國泰真全意住院醫療險",
                  "annual_premium": 11760,
                  "monthly_premium": 980,
                  "risk_adjustment": 1.0,
                  "breakdown": { "base": 980, "risk_loading": 0, "discount": 0 }
                },
                {
                  "product_id": "cathay-ci-001",
                  "product_name": "國泰醫卡實在重大傷病險",
                  "annual_premium": 21600,
                  "monthly_premium": 1800,
                  "risk_adjustment": 1.0,
                  "breakdown": { "base": 1800, "risk_loading": 0, "discount": 0 }
                }
              ],
              "total_annual": 33360,
              "total_monthly": 2780
            },
            "mediaType": "application/json"
          }
        ]
      }
    ]
  }
}
```

### 4. Compliance Check Agent

#### 投保資格檢查

**Request：**

```json
{
  "message": {
    "messageId": "msg-004",
    "role": "ROLE_USER",
    "contextId": "conv-abc",
    "parts": [
      {
        "data": {
          "skill": "compliance-verify",
          "age": 35,
          "product_category": "醫療險",
          "sum_insured": 200000,
          "annual_income": 800000,
          "annual_premium_total": 42000
        },
        "mediaType": "application/json"
      }
    ]
  }
}
```

**Response：**

```json
{
  "message": {
    "messageId": "msg-004-resp",
    "role": "ROLE_AGENT",
    "contextId": "conv-abc",
    "parts": [
      {
        "data": {
          "eligible": true,
          "checks": [
            { "rule": "age_range", "passed": true, "detail": "35歲在承保範圍 0-70 歲內" },
            { "rule": "medical_exam", "passed": true, "detail": "保額未超過免體檢額度" },
            { "rule": "financial_check", "passed": true, "detail": "年繳保費佔年收入 5.3%，未超過 30%" },
            { "rule": "minor_restriction", "passed": true, "detail": "非未成年人，無限制" }
          ],
          "warnings": []
        },
        "mediaType": "application/json"
      }
    ]
  }
}
```

> 注意：Compliance Check 是簡單的同步檢查，直接回傳 `Message` 而非 `Task`。
> A2A spec 允許 `SendMessage` 回傳 `Task` 或 `Message`。

---

## Orchestrator Streaming（A2A SSE）

Recommendation Agent 是唯一支援 streaming 的 agent。
前端透過 `POST /message:stream` 與 orchestrator 通訊。

### 前端 → Orchestrator

```
POST http://localhost:8200/message:stream
Content-Type: application/json
A2A-Version: 1.0

{
  "message": {
    "messageId": "msg-user-001",
    "role": "ROLE_USER",
    "contextId": "conv-abc",
    "parts": [
      { "text": "我35歲男性，工程師，想買醫療險，預算月繳5000" }
    ]
  }
}
```

### Orchestrator → 前端（SSE Stream）

SSE 回傳 A2A `StreamResponse` 格式。每個 `data:` 行包含一個 StreamResponse 物件。

```
HTTP/1.1 200 OK
Content-Type: text/event-stream

data: {"task":{"id":"task-main-001","contextId":"conv-abc","status":{"state":"TASK_STATE_WORKING","message":{"role":"ROLE_AGENT","parts":[{"text":"收到！正在檢查投保資格..."}]}}}}

data: {"statusUpdate":{"taskId":"task-main-001","contextId":"conv-abc","status":{"state":"TASK_STATE_WORKING","message":{"role":"ROLE_AGENT","parts":[{"text":"✅ 投保資格確認通過"}]}}}}

data: {"statusUpdate":{"taskId":"task-main-001","contextId":"conv-abc","status":{"state":"TASK_STATE_WORKING","message":{"role":"ROLE_AGENT","parts":[{"text":"正在評估風險..."}]}}}}

data: {"artifactUpdate":{"taskId":"task-main-001","contextId":"conv-abc","artifact":{"artifactId":"risk-result","name":"風險預評估","parts":[{"data":{"score":85,"risk_class":"preferred","factors":[{"name":"age","score":80,"level":"medium"},{"name":"bmi","score":90,"level":"standard"},{"name":"occupation","score":95,"level":"low"},{"name":"smoking","score":100,"level":"excellent"},{"name":"conditions","score":100,"level":"excellent"},{"name":"family_history","score":100,"level":"excellent"}],"prediction":"健康狀況良好，可享優良體費率"},"mediaType":"application/json"}]}}}

data: {"statusUpdate":{"taskId":"task-main-001","contextId":"conv-abc","status":{"state":"TASK_STATE_WORKING","message":{"role":"ROLE_AGENT","parts":[{"text":"正在搜尋商品..."}]}}}}

data: {"artifactUpdate":{"taskId":"task-main-001","contextId":"conv-abc","artifact":{"artifactId":"products-result","name":"商品推薦","parts":[{"data":{"products":[{"product_id":"cathay-medical-001","name":"國泰真全意住院醫療險","monthly_premium":980},{"product_id":"fubon-medical-001","name":"富邦人生自由行醫療險","monthly_premium":1150}]},"mediaType":"application/json"}]}}}

data: {"statusUpdate":{"taskId":"task-main-001","contextId":"conv-abc","status":{"state":"TASK_STATE_WORKING","message":{"role":"ROLE_AGENT","parts":[{"text":"正在試算保費..."}]}}}}

data: {"artifactUpdate":{"taskId":"task-main-001","contextId":"conv-abc","artifact":{"artifactId":"premium-result","name":"保費試算","parts":[{"data":{"results":[{"product_id":"cathay-medical-001","product_name":"國泰真全意住院醫療險","monthly_premium":980},{"product_id":"fubon-medical-001","product_name":"富邦人生自由行醫療險","monthly_premium":1150}],"total_monthly":980},"mediaType":"application/json"}]}}}

data: {"statusUpdate":{"taskId":"task-main-001","contextId":"conv-abc","status":{"state":"TASK_STATE_COMPLETED","message":{"role":"ROLE_AGENT","parts":[{"text":"以上是推薦方案，需要調整嗎？"}]}}}}

```

### 多輪對話（Multi-Turn）

用戶追問時，帶上同一個 `contextId` 和 `taskId`：

```json
{
  "message": {
    "messageId": "msg-user-002",
    "role": "ROLE_USER",
    "contextId": "conv-abc",
    "taskId": "task-main-001",
    "parts": [
      { "text": "如果加重大傷病險呢？" }
    ]
  }
}
```

Orchestrator 收到後，從 context 中取得之前的風險評估結果，只需要額外呼叫 product-catalog 和 premium-calculator，不需要重新做風險評估。

### INPUT_REQUIRED（追問缺少資訊）

當用戶訊息缺少必要資訊時，orchestrator 回傳 `TASK_STATE_INPUT_REQUIRED`：

```
data: {"task":{"id":"task-main-002","contextId":"conv-abc","status":{"state":"TASK_STATE_INPUT_REQUIRED","message":{"role":"ROLE_AGENT","parts":[{"text":"請告訴我你的年齡，以及想了解哪類保險？例如：壽險、醫療險、重大傷病、意外險、長照險、年金險"}]}}}}
```

前端收到 `INPUT_REQUIRED` 後，等待用戶輸入，再送出帶 `taskId` 的 follow-up message。

---

## 前端輔助 API

除了 A2A 標準端點外，Backend 額外提供兩個輔助 API 給前端使用：

### GET /agents/status

查詢所有 agent 在 Harbor 的狀態（非 A2A 標準，Harbor 專屬）。

**Response：**

```json
{
  "agents": [
    {
      "agent_id": "product-catalog-agent",
      "name": "商品目錄 Agent",
      "lifecycle": "published",
      "health": "healthy",
      "a2a_url": "http://localhost:8201"
    },
    {
      "agent_id": "underwriting-risk-agent",
      "name": "風險預評估 Agent",
      "lifecycle": "published",
      "health": "healthy",
      "a2a_url": "http://localhost:8202"
    }
  ]
}
```

### GET /agents/{id}/agent-card

取得指定 agent 的 A2A Agent Card（proxy 到 agent 的 `/.well-known/agent-card.json`）。

---

## 前端 Artifact 渲染對應

前端根據 Artifact 的 `name` 或 `data` 結構分派到對應的 UI component：

| Artifact name | data 結構特徵 | 前端 Component |
|---------------|-------------|---------------|
| `風險預評估` / `risk-*` | 含 `score`, `risk_class`, `factors` | `RiskCard` |
| `商品推薦` / `products-*` | 含 `products` array | `ProductCard` |
| `保費試算` / `premium-*` | 含 `results`, `total_monthly` | `PremiumTable` |
| `合規檢查` / `compliance-*` | 含 `eligible`, `checks` | `ComplianceStatus` |

Status message 中的 `text` Part 直接渲染為聊天氣泡。

---

## 完整呼叫流程（A2A 版）

```
用戶: "我30歲女性，想做完整保險規劃，預算年繳6萬"
                    │
                    ▼
         ┌──────────────────────────┐
         │ Frontend                  │
         │ POST /message:stream      │
         │ A2A SendMessageRequest    │
         └──────────┬───────────────┘
                    │
                    ▼
         ┌──────────────────────────┐
         │ Recommendation Agent      │
         │ (A2A Server, streaming)   │
         │                           │
         │ 1. Parse intent           │
         │ 2. Harbor discover        │
         │ 3. Harbor policy check    │
         └──────────┬───────────────┘
                    │
    ┌───────────────┼───────────────────────────────┐
    ▼               ▼               ▼               ▼
 Compliance      Risk Agent      Product Agent   Premium Agent
 Agent                                            
 POST             POST            POST            POST
 /message:send    /message:send   /message:send   /message:send
 (A2A)            (A2A)           (A2A)           (A2A)
    │               │               │               │
    ▼               ▼               ▼               ▼
 Message          Task+Artifact   Task+Artifact   Task+Artifact
 (eligible:true)  (risk_class:    (products:[..]) (total:3500)
                   preferred)
    │               │               │               │
    └───────────────┼───────────────┘───────────────┘
                    │
                    ▼ SSE StreamResponse events
         ┌──────────────────────────┐
         │ Frontend                  │
         │                           │
         │ statusUpdate → 聊天氣泡    │
         │ artifactUpdate → Rich Card│
         │ COMPLETED → 結束 stream   │
         └──────────────────────────┘
```

---

## Pydantic Models（Backend 實作參考）

以下是 Backend 實作時需要的 Pydantic model，對應 A2A 的 data model：

```python
# --- A2A Core Models ---

class Part(BaseModel):
    text: str | None = None
    data: dict[str, Any] | None = None
    raw: str | None = None          # base64
    url: str | None = None
    media_type: str | None = Field(None, alias="mediaType")
    filename: str | None = None
    metadata: dict[str, Any] | None = None

class Message(BaseModel):
    message_id: str = Field(alias="messageId")
    role: str                       # "ROLE_USER" | "ROLE_AGENT"
    context_id: str | None = Field(None, alias="contextId")
    task_id: str | None = Field(None, alias="taskId")
    parts: list[Part]
    metadata: dict[str, Any] | None = None

class Artifact(BaseModel):
    artifact_id: str = Field(alias="artifactId")
    name: str | None = None
    description: str | None = None
    parts: list[Part]
    metadata: dict[str, Any] | None = None

class TaskStatus(BaseModel):
    state: str                      # TASK_STATE_*
    message: Message | None = None
    timestamp: str | None = None

class Task(BaseModel):
    id: str
    context_id: str | None = Field(None, alias="contextId")
    status: TaskStatus
    artifacts: list[Artifact] | None = None
    history: list[Message] | None = None
    metadata: dict[str, Any] | None = None

class SendMessageRequest(BaseModel):
    message: Message
    configuration: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

# --- A2A Streaming Events ---

class TaskStatusUpdateEvent(BaseModel):
    task_id: str = Field(alias="taskId")
    context_id: str = Field(alias="contextId")
    status: TaskStatus

class TaskArtifactUpdateEvent(BaseModel):
    task_id: str = Field(alias="taskId")
    context_id: str = Field(alias="contextId")
    artifact: Artifact
    append: bool | None = None
    last_chunk: bool | None = Field(None, alias="lastChunk")

class StreamResponse(BaseModel):
    """A2A StreamResponse — exactly one field must be set."""
    task: Task | None = None
    message: Message | None = None
    status_update: TaskStatusUpdateEvent | None = Field(None, alias="statusUpdate")
    artifact_update: TaskArtifactUpdateEvent | None = Field(None, alias="artifactUpdate")

# --- Domain-specific data (inside Part.data) ---

class Product(BaseModel):
    product_id: str
    provider: str
    name: str
    category: str
    sub_type: str = ""
    age_range: dict[str, int] = Field(default_factory=lambda: {"min": 0, "max": 75})
    coverage: dict[str, Any] = Field(default_factory=dict)
    base_premium_monthly: int
    highlights: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)

class RiskFactor(BaseModel):
    name: str
    score: int
    weight: float
    level: str
    detail: str

class RiskAssessment(BaseModel):
    score: int
    risk_class: str
    bmi: float
    factors: list[RiskFactor]
    prediction: str
    premium_impact: str

class PremiumResult(BaseModel):
    product_id: str
    product_name: str
    annual_premium: int
    monthly_premium: int
    risk_adjustment: float
    breakdown: dict[str, int]

class ComplianceCheck(BaseModel):
    rule: str
    passed: bool
    detail: str

class ComplianceResult(BaseModel):
    eligible: bool
    checks: list[ComplianceCheck]
    warnings: list[str] = Field(default_factory=list)
```

> 注意：A2A spec 要求 JSON field 使用 camelCase。Pydantic model 使用 `Field(alias=...)` 處理。
