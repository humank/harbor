# 壽險 AI Agent 協作平台 — Sample Project

> 透過一個壽險商品查詢與風險預評估的場景，驗證 Harbor 的 agent 註冊、發現、生命週期管理與策略治理的完整流程。

---

## 專案目標

1. 建立一個簡單的 Web App，讓客戶輸入需求後，由多個 AI Agent 協作完成壽險商品推薦
2. 所有 Agent 透過 Harbor 註冊、上架、發現，驗證完整的 agent lifecycle
3. 透過 Harbor 的 policy 機制控制 agent 間的通訊權限與資料分級

---

## 業務背景

### 問題場景

客戶想買保險，但面對國泰人壽、富邦人壽等多家保險公司的數十種商品，不知道：
- 哪些商品適合自己？
- 自己的健康狀況能不能通過核保？
- 保費大概多少？

### 解決方案

透過多個專責 Agent 協作，提供「商品查詢 → 風險預評估 → 保費試算 → 方案推薦」的一站式服務。

---

## Agent 設計

### 總覽

| Agent ID | 名稱 | Capabilities | 說明 |
|----------|------|-------------|------|
| `product-catalog-agent` | 商品目錄 Agent | `product_search`, `product_comparison` | 查詢壽險商品，依需求篩選推薦 |
| `underwriting-risk-agent` | 風險預評估 Agent | `risk_assessment`, `risk_scoring` | 根據被保險人資料做核保風險預評估 |
| `premium-calculator-agent` | 保費試算 Agent | `premium_calculation`, `quote_generation` | 根據商品 + 風險等級試算保費 |
| `compliance-check-agent` | 合規檢查 Agent | `kyc_check`, `regulatory_compliance` | 確認投保資格與法規限制 |
| `recommendation-agent` | 推薦引擎 Agent | `plan_recommendation`, `needs_analysis` | Orchestrator，整合所有結果產出建議 |
| `explanation-agent` | 保險知識 Agent | `term_explanation`, `faq` | 用白話文解釋保險術語和條款（新增） |

### Agent 詳細規格

#### 1. Product Catalog Agent

- **職責**：管理國泰人壽、富邦人壽的商品資料，提供查詢與比較
- **輸入**：客戶年齡、需求類型（壽險/醫療/意外/年金等）、預算
- **輸出**：符合條件的商品清單，含保障內容摘要
- **資料來源**：靜態商品資料（JSON），模擬兩家保險公司的商品目錄

商品分類：

| 類別 | 國泰人壽商品（模擬） | 富邦人壽商品（模擬） |
|------|---------------------|---------------------|
| 終身壽險 | 國泰鑫利率變動型終身壽險 | 富邦利率變動型終身壽險 |
| 定期壽險 | 國泰e定保定期壽險 | 富邦e指定定期壽險 |
| 醫療險 | 國泰真全意住院醫療險 | 富邦人生自由行醫療險 |
| 重大傷病 | 國泰醫卡實在重大傷病險 | 富邦一次到位重大傷病險 |
| 意外險 | 國泰安心意外傷害險 | 富邦安泰意外傷害險 |
| 長照險 | 國泰呵護長期照顧險 | 富邦長期照顧終身健康險 |
| 年金險 | 國泰利變年金保險 | 富邦利變年金保險 |
| 投資型 | 國泰變額壽險 | 富邦變額萬能壽險 |

> 注意：以上商品名稱為模擬用途，非真實商品名稱。

#### 2. Underwriting Risk Agent

- **職責**：根據被保險人資料進行風險預評估（非正式核保）
- **輸入**：年齡、性別、BMI、職業類別、吸菸狀態、既往症、家族病史
- **輸出**：風險等級 + 各因子評分 + 核保預測（標準體/次標準體/加費/拒保）

風險評估因子：

| 因子 | 評分規則 | 權重 |
|------|---------|------|
| 年齡 | 18-35: 低風險 / 36-50: 中風險 / 51-65: 高風險 / 65+: 極高 | 20% |
| BMI | 18-24: 優良 / 25-29: 標準 / 30-34: 次標準 / 35+: 高風險 | 20% |
| 職業類別 | 第1-2類: 低風險 / 第3-4類: 中風險 / 第5-6類: 高風險 | 15% |
| 吸菸 | 非吸菸: 優良 / 已戒菸>1年: 標準 / 吸菸中: 高風險 | 15% |
| 既往症 | 無: 優良 / 已控制慢性病: 次標準 / 未控制或重大疾病: 高風險 | 20% |
| 家族病史 | 無: 優良 / 60歲後發病: 標準 / 60歲前心臟病或癌症: 高風險 | 10% |

風險等級對應：

| 等級 | 分數區間 | 核保預測 | 保費影響 |
|------|---------|---------|---------|
| Preferred Plus | 90-100 | 優選體，最低費率 | 基準費率 |
| Preferred | 75-89 | 優良體 | +0~10% |
| Standard Plus | 60-74 | 標準體偏優 | +10~25% |
| Standard | 40-59 | 標準體 | +25~50% |
| Substandard | 20-39 | 次標準體，需加費 | +50~150% |
| Decline | 0-19 | 可能拒保 | N/A |

> ⚠️ 免責聲明：此為模擬預評估，非正式核保結果。實際核保以保險公司審核為準。

#### 3. Premium Calculator Agent

- **職責**：根據商品、保額、風險等級試算保費
- **輸入**：商品 ID、保額、繳費年期、被保險人年齡、風險等級
- **輸出**：年繳/月繳保費金額

#### 4. Compliance Check Agent

- **職責**：檢查投保資格與法規限制
- **輸入**：被保險人年齡、商品類型、保額
- **輸出**：是否符合投保資格 + 限制說明

檢查項目：
- 年齡是否在商品承保範圍內（如終身壽險通常 0-70 歲）
- 保額是否超過免體檢額度（如壽險 500 萬以上需體檢）
- 是否需要財力證明（如年繳保費超過年收入 30%）
- 未成年人投保限制（15 歲以下不得有死亡給付）

#### 5. Recommendation Agent（Orchestrator）

- **職責**：接收客戶需求，協調其他 Agent，產出最終推薦方案
- **輸入**：客戶自然語言需求
- **輸出**：完整的保險規劃建議書（含商品、保費、風險說明）
- **依賴**：呼叫其他 4 個 Agent

---

## 使用情境

### 情境一：商品查詢

```
客戶：「我 35 歲，想買醫療險和重大傷病險，預算每月 5000 元」

流程：
1. recommendation-agent 解析需求
2. → product-catalog-agent.search({age: 35, types: ["醫療險", "重大傷病"], budget: 5000/月})
3. ← 回傳國泰 + 富邦共 4-6 個候選商品
4. recommendation-agent 整理後回覆客戶
```

### 情境二：風險預評估

```
客戶：「我先生 42 歲，身高 175cm 體重 85kg，有高血壓吃藥控制，工程師，不抽菸」

流程：
1. recommendation-agent 解析被保險人資料
2. → underwriting-risk-agent.assess({
       age: 42,
       gender: "male",
       bmi: 27.8,          // 85 / 1.75^2
       occupation_class: 1, // 內勤工程師
       smoking: "never",
       conditions: ["hypertension_controlled"],
       family_history: []
   })
3. ← 回傳：
   {
     risk_class: "Standard Plus",
     score: 68,
     factors: {
       age: {score: 70, level: "中風險"},
       bmi: {score: 75, level: "標準"},
       occupation: {score: 95, level: "低風險"},
       smoking: {score: 100, level: "優良"},
       conditions: {score: 40, level: "次標準"},
       family_history: {score: 100, level: "優良"}
     },
     prediction: "可正常承保，高血壓部分可能加費 10-25%",
     disclaimer: "此為預評估結果，非正式核保決定"
   }
```

### 情境三：完整規劃流程

```
客戶：「我 30 歲女性，剛結婚，想做完整的保險規劃，預算年繳 6 萬」

完整協作流程：
1. recommendation-agent 接收需求，拆解為子任務

2. → compliance-check-agent：確認基本投保資格
   ← OK，30 歲無特殊限制

3. → underwriting-risk-agent：風險預評估（假設健康良好）
   ← Preferred，score: 88

4. → product-catalog-agent：查詢適合 30 歲女性的商品組合
   ← 推薦組合：
      - 定期壽險 500 萬（保障家庭責任）
      - 實支實付醫療險（住院/手術保障）
      - 重大傷病險 100 萬（一次給付）
      - 意外險 200 萬（含意外醫療）

5. → premium-calculator-agent：試算各商品保費
   ← 年繳保費明細：
      - 定期壽險：8,500 元
      - 醫療險：12,000 元
      - 重大傷病：18,000 元
      - 意外險：3,500 元
      - 合計：42,000 元（在 60,000 預算內）

6. recommendation-agent 產出建議書，含：
   - 推薦方案摘要
   - 各商品保障內容比較（國泰 vs 富邦）
   - 保費明細
   - 風險預評估結果
   - 免責聲明
```

---

## Harbor 整合

### Agent 註冊

每個 Agent 部署後，透過 Harbor API 註冊：

```bash
# 商品目錄 Agent
harbor register product-catalog-agent "商品目錄 Agent" \
  --capabilities product_search,product_comparison \
  --provider on-prem \
  --protocol http \
  --endpoint http://localhost:8200/product-catalog

# 風險預評估 Agent
harbor register underwriting-risk-agent "風險預評估 Agent" \
  --capabilities risk_assessment,risk_scoring \
  --provider on-prem \
  --protocol http \
  --endpoint http://localhost:8200/underwriting-risk

# 保費試算 Agent
harbor register premium-calculator-agent "保費試算 Agent" \
  --capabilities premium_calculation,quote_generation \
  --provider on-prem \
  --protocol http \
  --endpoint http://localhost:8200/premium-calculator

# 合規檢查 Agent
harbor register compliance-check-agent "合規檢查 Agent" \
  --capabilities kyc_check,regulatory_compliance \
  --provider on-prem \
  --protocol http \
  --endpoint http://localhost:8200/compliance-check

# 推薦引擎 Agent（Orchestrator）
harbor register recommendation-agent "推薦引擎 Agent" \
  --capabilities plan_recommendation,needs_analysis \
  --provider on-prem \
  --protocol http \
  --endpoint http://localhost:8200/recommendation
```

### Lifecycle 上架流程

驗證 Harbor 的完整 lifecycle pipeline：

```bash
# 1. 註冊後為 draft 狀態
harbor list
# → 5 個 agent，全部 lifecycle: draft

# 2. 提交審核
harbor lifecycle product-catalog-agent submitted
harbor lifecycle underwriting-risk-agent submitted
harbor lifecycle premium-calculator-agent submitted
harbor lifecycle compliance-check-agent submitted
harbor lifecycle recommendation-agent submitted

# 3. 審核通過（dev 環境 auto-approve）
# → lifecycle: approved → published

# 4. 驗證 discovery
harbor discover -c product_search --resolve
# → 回傳 product-catalog-agent

harbor discover -c risk_assessment --resolve
# → 回傳 underwriting-risk-agent

# 5. 測試 suspend（緊急下架）
harbor lifecycle underwriting-risk-agent suspended --reason "資料外洩疑慮"
harbor discover -c risk_assessment --resolve
# → 無結果（suspended 不可被發現）

# 6. 恢復上架
harbor lifecycle underwriting-risk-agent published
```

### Policy 設定

#### Capability Boundary（風險預評估 Agent）

```yaml
# underwriting-risk-agent 的能力邊界
tools:
  allowed:
    - "risk_scoring_engine"
    - "bmi_calculator"
    - "occupation_class_lookup"
  denied:
    - "medical_record_access"    # 不可直接存取病歷
    - "credit_score_lookup"      # 不可查信用分數
  require_human:
    - "decline_recommendation"   # 建議拒保需人工確認
data_classification:
  max_level: "confidential"      # 可處理機密等級資料
```

#### Communication ACL

```yaml
# Agent 間通訊規則
rules:
  # recommendation-agent 可以呼叫所有其他 agent
  - from: "recommendation-agent"
    to: "product-catalog-agent"
    allowed: true
  - from: "recommendation-agent"
    to: "underwriting-risk-agent"
    allowed: true
  - from: "recommendation-agent"
    to: "premium-calculator-agent"
    allowed: true
  - from: "recommendation-agent"
    to: "compliance-check-agent"
    allowed: true

  # premium-calculator 需要查商品資料
  - from: "premium-calculator-agent"
    to: "product-catalog-agent"
    allowed: true

  # 禁止外部直接呼叫風險評估（必須透過 recommendation-agent）
  - from: "external-*"
    to: "underwriting-risk-agent"
    allowed: false

  # 禁止風險評估 agent 反向呼叫推薦引擎（防止循環）
  - from: "underwriting-risk-agent"
    to: "recommendation-agent"
    allowed: false
```

#### Schedule Window

```yaml
# 風險預評估 Agent 僅在營業時間運作
active_windows:
  - cron: "0 9-18 * * MON-FRI"
    timezone: "Asia/Taipei"
out_of_window_action: "reject"
```

---

## Web App 規格

### 為什麼用聊天介面

傳統表單式 UI 會把 orchestrator 的工作硬編碼在前端，失去 multi-agent 協作的意義。聊天介面的優勢：

1. **自然語言驅動** — 客戶說「我 35 歲想買醫療險」，recommendation-agent 自行拆解任務、呼叫其他 agent
2. **過程透明化** — 即時顯示「正在查詢商品...」「正在評估風險...」，讓用戶看到 agent 協作過程
3. **多輪對話** — 客戶可追問「如果我戒菸一年呢？」「換成富邦的方案呢？」
4. **Rich Content** — 在聊天氣泡中嵌入結構化卡片（商品比較表、風險雷達圖、保費明細）

### 設計系統（ui-ux-pro-max 生成）

```
風格：Trust & Authority
字體：IBM Plex Sans（financial, trustworthy, professional）
配色：
  Primary:    #F59E0B  (Gold — 信任感)
  Secondary:  #FBBF24
  CTA:        #8B5CF6  (Purple — 科技感)
  Background: #0F172A  (Dark slate)
  Text:       #F8FAFC
效果：Badge hover effects, metric pulse animations, smooth stat reveal
避免：Confusing pricing / No trust signals / AI purple-pink gradients
```

> 實作時須透過 `ui-ux-pro-max --design-system --persist` 產生完整 design token，
> 並遵循 pre-delivery checklist（無 emoji icon、cursor-pointer、contrast 4.5:1、prefers-reduced-motion）。

### 頁面結構

整個 App 只有一個主頁面，左右分欄：

```
┌──────────────────────────────────────────────────────────┐
│  Harbor Insurance Demo                          [?] [⚙]  │
├────────────────────┬─────────────────────────────────────┤
│                    │                                      │
│   Agent 狀態面板    │         聊天主區域                    │
│                    │                                      │
│  ┌──────────────┐  │  ┌──────────────────────────────┐   │
│  │ 🟢 商品目錄   │  │  │ 🤖 你好！我是保險規劃助理。    │   │
│  │ 🟢 風險預評估 │  │  │    請告訴我你的需求，例如：    │   │
│  │ 🟢 保費試算   │  │  │    「我30歲，想買醫療險」      │   │
│  │ 🟢 合規檢查   │  │  └──────────────────────────────┘   │
│  │ 🟢 推薦引擎   │  │                                      │
│  └──────────────┘  │  ┌──────────────────────────────┐   │
│                    │  │ 👤 我35歲男性，工程師，想買     │   │
│  ┌──────────────┐  │  │    醫療險和重大傷病險，         │   │
│  │ 本次協作流程  │  │  │    預算每月5000                │   │
│  │              │  │  └──────────────────────────────┘   │
│  │ recommend    │  │                                      │
│  │  ├→ comply ✓ │  │  ┌──────────────────────────────┐   │
│  │  ├→ risk  ✓  │  │  │ 🤖 收到！讓我幫你規劃。       │   │
│  │  ├→ catalog… │  │  │                                │   │
│  │  └→ premium  │  │  │ ⏳ 正在檢查投保資格...          │   │
│  └──────────────┘  │  │ ✅ 合規檢查通過                 │   │
│                    │  │                                │   │
│                    │  │ ⏳ 正在評估風險...               │   │
│                    │  │ ✅ 風險等級：Preferred (82分)    │   │
│                    │  │                                │   │
│                    │  │ ⏳ 正在搜尋商品...               │   │
│                    │  │ ┌────────────────────────────┐ │   │
│                    │  │ │ [商品比較卡片]              │ │   │
│                    │  │ │ 國泰真全意 vs 富邦自由行    │ │   │
│                    │  │ │ 保額/保費/保障範圍比較      │ │   │
│                    │  │ └────────────────────────────┘ │   │
│                    │  └──────────────────────────────┘   │
│                    │                                      │
│                    │  ┌──────────────────────────────┐   │
│                    │  │ [輸入框]          [送出]       │   │
│                    │  └──────────────────────────────┘   │
├────────────────────┴─────────────────────────────────────┤
│  ⚠️ 免責聲明：本服務僅供參考，非正式核保或保險銷售建議      │
└──────────────────────────────────────────────────────────┘
```

### 聊天訊息類型

| 類型 | 說明 | 呈現方式 |
|------|------|---------|
| `text` | 純文字對話 | 一般聊天氣泡 |
| `agent_status` | Agent 執行狀態 | 帶 spinner/checkmark 的狀態列 |
| `risk_card` | 風險評估結果 | 嵌入式卡片：分數條 + 各因子雷達圖 |
| `product_comparison` | 商品比較 | 並排比較表格卡片 |
| `premium_summary` | 保費明細 | 明細表格 + 總計 |
| `report` | 完整建議書 | 可展開的摘要卡片，含下載按鈕 |
| `agent_flow` | Agent 協作流程 | 即時更新的流程圖（左側面板同步顯示） |

### 對話流程範例

```
🤖: 你好！我是保險規劃助理。請告訴我你的需求。

👤: 我35歲男性，工程師，想買醫療險，預算月繳5000

🤖: 收到！我來幫你規劃。先確認一些資訊：
    身高體重大約多少？有沒有抽菸？有沒有慢性病？

👤: 175cm 78kg，不抽菸，沒有慢性病

🤖: [agent_status] ⏳ 正在檢查投保資格... → ✅ 通過
    [agent_status] ⏳ 正在評估風險...
    [risk_card] 風險等級：Preferred (85分)
      年齡: ★★★★☆  BMI: ★★★★☆  職業: ★★★★★
      吸菸: ★★★★★  既往症: ★★★★★  家族史: ★★★★★
    
    你的健康狀況很好！以下是適合你的醫療險：
    
    [product_comparison]
    ┌─────────────┬──────────────┐
    │ 國泰真全意   │ 富邦自由行    │
    ├─────────────┼──────────────┤
    │ 實支實付     │ 實支實付      │
    │ 病房 2000/日 │ 病房 2500/日  │
    │ 手術 20萬    │ 手術 25萬     │
    │ 月繳 980     │ 月繳 1,150    │
    └─────────────┴──────────────┘
    
    [premium_summary] 推薦方案月繳合計：4,280 元（在預算內）
    
    需要我詳細說明哪個商品嗎？或者要加入其他險種？

👤: 如果加重大傷病險呢？

🤖: [agent_status] ⏳ 正在搜尋重大傷病險...
    [product_comparison] 新增重大傷病險比較...
    [premium_summary] 更新後月繳合計：5,780 元（超出預算 780 元）
    
    稍微超出預算，要調整保額還是移除某個項目？
```

### UX 規範

- **Streaming 回應**：agent 回覆使用 typewriter effect 逐字顯示，不要等全部完成才顯示
- **Loading 狀態**：每個 agent 呼叫顯示 skeleton / pulse animation，完成後轉為 checkmark
- **Rich Card**：商品比較、風險評估等結構化資料用嵌入式卡片呈現，不要純文字
- **左側面板**：即時顯示 agent 狀態（online/offline）和本次對話的協作流程圖
- **免責聲明**：固定在底部，始終可見
- **Responsive**：mobile 時左側面板收合為 drawer

---

## 技術架構

```
┌─────────────────────────────────────────────────┐
│              Web App (React + Chat UI)            │
│         samples/life-insurance/frontend/          │
└──────────────────────┬──────────────────────────┘
                       │ WebSocket / SSE (streaming)
                       ▼
┌─────────────────────────────────────────────────┐
│            Sample Backend (FastAPI)               │
│         samples/life-insurance/backend/           │
│                                                   │
│  POST /chat  ← 接收用戶訊息                       │
│  SSE stream  → 回傳 agent 狀態 + 結果              │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │         recommendation-agent (orchestrator)  │ │
│  │                                               │ │
│  │  1. 解析用戶意圖                               │ │
│  │  2. Harbor discover → 找到需要的 agent         │ │
│  │  3. Harbor policy evaluate → 檢查通訊權限      │ │
│  │  4. 呼叫各 agent，stream 狀態回前端             │ │
│  │  5. 彙整結果，產出結構化回覆                     │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────┘
                       │
          ┌────────────┼────────────┬──────────────┐
          ▼            ▼            ▼              ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ product  │ │underwrite│ │ premium  │ │compliance│
   │ catalog  │ │  risk    │ │   calc   │ │  check   │
   └──────────┘ └──────────┘ └──────────┘ └──────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   Harbor API    │
              │  (registry,     │
              │   discovery,    │
              │   policy)       │
              └─────────────────┘
```

### Tech Stack

| 層級 | 技術 |
|------|------|
| Frontend | React + Tailwind CSS + Vite |
| Chat Streaming | A2A `POST /message:stream` + SSE（StreamResponse 格式） |
| Agent 通訊 | A2A v1.0 HTTP+JSON binding（`POST /message:send`） |
| Backend / Agents | Python + FastAPI（每個 agent 獨立 A2A Server） |
| Agent Registry | Harbor API（本地 localhost:8100） |
| 資料 | 靜態 JSON（模擬商品資料） |
| 設計系統 | ui-ux-pro-max 生成（Trust & Authority 風格） |

### Backend API（A2A Endpoints）

每個 agent 是獨立的 A2A Server：

| Agent | Port | A2A Endpoints |
|-------|------|--------------|
| Recommendation (Orchestrator) | 8200 | `POST /message:send`, `POST /message:stream`, `GET /.well-known/agent-card.json` |
| Product Catalog | 8201 | `POST /message:send`, `GET /.well-known/agent-card.json` |
| Underwriting Risk | 8202 | `POST /message:send`, `GET /.well-known/agent-card.json` |
| Premium Calculator | 8203 | `POST /message:send`, `GET /.well-known/agent-card.json` |
| Compliance Check | 8204 | `POST /message:send`, `GET /.well-known/agent-card.json` |

輔助 API（非 A2A，Harbor 專屬）：

| Method | Path | 說明 |
|--------|------|------|
| GET | `/agents/status` | 查詢所有 agent 的 Harbor 狀態 |
| GET | `/agents/{id}/agent-card` | Proxy 取得 agent 的 A2A Agent Card |

SSE 事件格式（A2A StreamResponse）：

```
data: {"task":{"id":"task-001","contextId":"conv-abc","status":{"state":"TASK_STATE_WORKING","message":{"role":"ROLE_AGENT","parts":[{"text":"正在檢查投保資格..."}]}}}}

data: {"statusUpdate":{"taskId":"task-001","contextId":"conv-abc","status":{"state":"TASK_STATE_WORKING","message":{"role":"ROLE_AGENT","parts":[{"text":"✅ 合規檢查通過"}]}}}}

data: {"artifactUpdate":{"taskId":"task-001","contextId":"conv-abc","artifact":{"artifactId":"risk-result","name":"風險預評估","parts":[{"data":{"score":85,"risk_class":"preferred"},"mediaType":"application/json"}]}}}

data: {"statusUpdate":{"taskId":"task-001","contextId":"conv-abc","status":{"state":"TASK_STATE_COMPLETED","message":{"role":"ROLE_AGENT","parts":[{"text":"規劃完成！"}]}}}}
```

---

## 專案結構

```
samples/life-insurance/
├── requirement.md              # 本文件
├── architecture.md             # 架構規範
├── api-contract.md             # A2A API Contract
├── README.md                   # 快速啟動指南
├── data/
│   ├── products_cathay.json    # 國泰人壽模擬商品資料
│   ├── products_fubon.json     # 富邦人壽模擬商品資料
│   └── occupation_classes.json # 職業類別對照表
├── backend/
│   ├── main.py                 # 啟動所有 agent（各自獨立 port）
│   ├── agents/
│   │   ├── product_catalog.py  # A2A Server :8201
│   │   ├── underwriting_risk.py# A2A Server :8202
│   │   ├── premium_calculator.py# A2A Server :8203
│   │   ├── compliance_check.py # A2A Server :8204
│   │   └── recommendation.py   # A2A Server :8200（Orchestrator, streaming）
│   ├── a2a_client.py           # A2A HTTP+JSON client（呼叫其他 agent）
│   ├── a2a_models.py           # A2A Pydantic models（Task, Message, Part, Artifact...）
│   ├── harbor_client.py        # Harbor API 呼叫封裝
│   └── domain_models.py        # 業務資料模型（Product, RiskAssessment...）
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # 主頁面（左右分欄）
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx  # 聊天主區域
│   │   │   ├── ArtifactRenderer.tsx # 根據 artifact 分派到 Rich Card
│   │   │   ├── AgentPanel.tsx  # 左側 Agent 狀態面板
│   │   │   ├── RiskCard.tsx    # 風險評估卡片
│   │   │   ├── ProductCard.tsx # 商品比較卡片
│   │   │   └── PremiumTable.tsx# 保費明細表格
│   │   ├── hooks/
│   │   │   ├── useA2AStream.ts # A2A SSE StreamResponse 解析
│   │   │   └── useAgentStatus.ts# Agent 狀態輪詢
│   │   └── types/
│   │       └── a2a.ts          # A2A TypeScript 型別（Task, Message, Part...）
│   ├── tailwind.config.js      # 設計系統 token
│   └── package.json
└── scripts/
    ├── seed_harbor.sh          # 註冊所有 agent 到 Harbor
    └── run.sh                  # 一鍵啟動（Harbor + 5 agents + frontend）
```

---

## 開發里程碑

### Phase 1：資料與 Agent 骨架

- [ ] 建立模擬商品資料（JSON）
- [ ] 實作 5 個 Agent 的 FastAPI endpoint
- [ ] 每個 Agent 獨立可測試

### Phase 2：Harbor 整合

- [ ] 撰寫 seed script，將 5 個 Agent 註冊到 Harbor
- [ ] 走完 lifecycle：draft → submitted → published
- [ ] 設定 capability boundary、communication ACL、schedule policy
- [ ] recommendation-agent 透過 Harbor discover 找到其他 agent

### Phase 3：Chat Web App

- [ ] 用 ui-ux-pro-max 生成設計系統並 persist
- [ ] 聊天主介面（SSE streaming + typewriter effect）
- [ ] Rich message 卡片（風險評估、商品比較、保費明細）
- [ ] 左側 Agent 狀態面板 + 協作流程圖
- [ ] 多輪對話支援（追問、修改條件）
- [ ] Responsive（mobile drawer）

### Phase 4：驗證與展示

- [ ] 驗證 suspend 後 discovery 不回傳該 agent
- [ ] 驗證 communication ACL 阻擋未授權呼叫
- [ ] 驗證 schedule window 在非營業時間拒絕請求
- [ ] 驗證 audit trail 記錄所有操作
- [ ] 端到端 demo：從聊天輸入到建議書產出

---

## 注意事項

1. **架構規範**：開發前請先閱讀 [architecture.md](./architecture.md)，定義了分層架構、agent 模組結構、錯誤處理等規範
2. **API Contract**：所有 agent 的 request/response schema 定義在 [api-contract.md](./api-contract.md)
3. **Strands + Bedrock 整合**：LLM 整合與 AgentCore 部署設計見 [strands-integration.md](./strands-integration.md)
4. **非正式核保**：風險預評估僅供參考，UI 必須明確標示免責聲明
2. **模擬資料**：商品名稱與費率為模擬用途，非真實商品資訊
3. **PII 保護**：被保險人健康資料為高度敏感資訊，agent 的 `data_classification` 設為 `confidential`
4. **商品名稱**：為避免商標問題，商品名稱使用模擬名稱，不直接使用國泰/富邦的真實商品名
