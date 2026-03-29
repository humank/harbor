"""AgentCore Runtime entrypoint for the Recommendation (Orchestrator) agent.

AgentCore Runtime with ProtocolConfiguration=A2A expects the container to serve
A2A JSON-RPC on port 8080. Strands A2AServer does exactly this.
"""

import sys
import os
import json

sys.path.insert(0, "/app")

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

from backend.tools.product_search import search, compare
from backend.tools.risk_scoring import assess
from backend.tools.premium_calc import calc_batch
from backend.tools.compliance_rules import check

BEDROCK_MODEL = os.environ.get("BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0")


@tool
def check_compliance(age: int, product_category: str) -> str:
    """檢查投保資格。傳入年齡和商品類型（如「醫療險」「壽險」），回傳是否符合資格。"""
    return json.dumps(check(age, product_category), ensure_ascii=False)


@tool
def assess_risk(age: int = 30, height_cm: float = 170, weight_kg: float = 65,
                occupation_class: int = 1, smoking_status: str = "never",
                conditions: str = "none", family_history: str = "none") -> str:
    """評估被保險人的核保風險等級。傳入健康資料，回傳風險分數和等級。"""
    cond_list = [c.strip() for c in conditions.split(",")]
    fam_list = [f.strip() for f in family_history.split(",")]
    return json.dumps(assess(age, height_cm, weight_kg, occupation_class, smoking_status, cond_list, fam_list), ensure_ascii=False)


@tool
def search_products(age: int = 0, types: str = "", budget_monthly: int = 0) -> str:
    """搜尋適合的保險商品。types 為逗號分隔的險種（如「醫療險,重大傷病」）。"""
    type_list = [t.strip() for t in types.split(",") if t.strip()] if types else []
    return json.dumps(search(age, type_list, budget_monthly), ensure_ascii=False)


@tool
def calculate_premium(items_json: str) -> str:
    """試算保費。傳入 JSON 陣列，每個元素含 product_id, age, risk_class。"""
    return json.dumps(calc_batch(json.loads(items_json)), ensure_ascii=False)


SYSTEM_PROMPT = """你是專業的保險規劃顧問。根據客戶需求，協調多個專家完成保險規劃。

你有以下工具可以使用：
- check_compliance: 檢查投保資格
- assess_risk: 評估核保風險
- search_products: 搜尋適合的商品
- calculate_premium: 試算保費

工作流程：
1. 理解客戶需求（年齡、預算、想要的險種）
2. 如果資訊不足，先追問
3. 搜尋適合的商品
4. 試算保費
5. 用清楚易懂的方式彙整結果

用繁體中文回覆，金額用台幣表示。"""

agent = Agent(
    name="推薦引擎 Agent",
    description="根據客戶需求協調多個專家完成保險規劃",
    model=BEDROCK_MODEL,
    system_prompt=SYSTEM_PROMPT,
    tools=[check_compliance, assess_risk, search_products, calculate_premium],
)

if __name__ == "__main__":
    # A2AServer on port 9000 — AgentCore Runtime A2A protocol requires port 9000
    server = A2AServer(agent=agent, host="0.0.0.0", port=9000)
    server.serve()
