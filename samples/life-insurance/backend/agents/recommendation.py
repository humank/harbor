"""Recommendation Agent (Orchestrator) — discovers other agents via Harbor.

Agent discovery flow:
  1. Tool is called by LLM
  2. Tool calls harbor.discover(capability) to find the right agent
  3. Harbor returns the A2A endpoint URL of a PUBLISHED agent
  4. Tool creates A2AAgent with that URL and invokes it
  5. If Harbor is down, falls back to static URLs from config.py
"""

import asyncio
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from strands import Agent, tool
from strands.agent.a2a_agent import A2AAgent
from strands.multiagent.a2a import A2AServer

from config import AGENT_PORTS, BEDROCK_MODEL, USE_BEDROCK
from harbor_client import harbor

SELF_ID = "recommendation-agent"


async def _call_agent(capability: str, prompt: str) -> str:
    """Discover an agent via Harbor, check policy, then call it via A2A."""
    # 1. Discover
    url = await harbor.discover(capability)
    if not url:
        return f"[ERROR] 找不到具有 {capability} 能力的 agent（Harbor discover 失敗）"

    # 2. Policy check
    target_id = capability.replace("_", "-") + "-agent"
    allowed = await harbor.check_policy(SELF_ID, target_id)
    if not allowed:
        return f"[BLOCKED] Harbor policy 不允許 {SELF_ID} 呼叫 {target_id}"

    # 3. Call via A2A
    agent = A2AAgent(endpoint=url)
    result = agent(prompt)
    return str(result.message)


def _call_agent_sync(capability: str, prompt: str) -> str:
    """Sync wrapper for _call_agent (Strands tools are sync)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, _call_agent(capability, prompt)).result()
    return asyncio.run(_call_agent(capability, prompt))


# --- Tools that discover agents via Harbor ---

@tool
def check_compliance(age: int, product_category: str) -> str:
    """檢查投保資格。傳入年齡和商品類型（如「醫療險」「壽險」），回傳是否符合資格。"""
    return _call_agent_sync("kyc_check", f"檢查 {age} 歲投保 {product_category} 的資格")


@tool
def assess_risk(age: int, gender: str, height_cm: float, weight_kg: float,
                occupation_class: int = 1, smoking_status: str = "never",
                conditions: str = "none", family_history: str = "none") -> str:
    """評估被保險人的核保風險等級。傳入健康資料，回傳風險分數和等級。"""
    prompt = (f"評估風險：{age}歲{gender}，身高{height_cm}cm 體重{weight_kg}kg，"
              f"職業類別{occupation_class}，吸菸狀態:{smoking_status}，"
              f"既往症:{conditions}，家族史:{family_history}")
    return _call_agent_sync("risk_assessment", prompt)


@tool
def search_products(age: int, types: str, budget_monthly: int = 0) -> str:
    """搜尋適合的保險商品。types 為逗號分隔的險種（如「醫療險,重大傷病」）。"""
    return _call_agent_sync("product_search", f"搜尋 {age} 歲適合的 {types}，月預算 {budget_monthly}")


@tool
def calculate_premium(items_json: str) -> str:
    """試算保費。傳入 JSON 陣列，每個元素含 product_id, age, risk_class。"""
    return _call_agent_sync("premium_calculation", f"試算保費：{items_json}")


@tool
def explain_insurance_term(question: str) -> str:
    """解釋保險術語或概念。當客戶問「什麼是實支實付」等問題時使用。"""
    return _call_agent_sync("term_explanation", question)


SYSTEM_PROMPT = """你是專業的保險規劃顧問。根據客戶需求，協調多個專家完成保險規劃。

你有以下工具可以使用：
- check_compliance: 檢查投保資格
- assess_risk: 評估核保風險（需要身高體重等健康資料）
- search_products: 搜尋適合的商品
- calculate_premium: 試算保費
- explain_insurance_term: 解釋保險術語

工作流程：
1. 理解客戶需求（年齡、預算、想要的險種）
2. 如果資訊不足，先追問（至少需要年齡和想要的險種）
3. 檢查投保資格
4. 如果客戶提供了健康資訊（身高體重等），做風險預評估
5. 搜尋適合的商品
6. 試算保費
7. 用清楚易懂的方式彙整結果，包含商品比較和建議

注意事項：
- 風險預評估結果僅供參考，要提醒客戶
- 比較商品時要客觀，列出各自優缺點
- 保費超出預算時主動建議調整方案
- 用繁體中文回覆
- 金額用台幣表示"""

agent_kwargs = {
    "name": "推薦引擎 Agent",
    "description": "根據客戶需求協調多個 Agent 產出完整保險規劃建議",
    "system_prompt": SYSTEM_PROMPT,
    "tools": [check_compliance, assess_risk, search_products, calculate_premium, explain_insurance_term],
}
if USE_BEDROCK:
    agent_kwargs["model"] = BEDROCK_MODEL

orchestrator = Agent(**agent_kwargs)

if __name__ == "__main__":
    import os
    if os.environ.get("AGENTCORE_RUNTIME"):
        # Running inside AgentCore Runtime — use BedrockAgentCoreApp
        from bedrock_agentcore.runtime import BedrockAgentCoreApp
        app = BedrockAgentCoreApp()

        @app.entrypoint
        def invoke(payload):
            prompt = payload.get("prompt", "")
            result = orchestrator(prompt)
            return {"result": str(result.message)}

        app.run()
    else:
        # Local development — use Strands A2AServer
        server = A2AServer(agent=orchestrator, host="0.0.0.0", port=AGENT_PORTS["recommendation"])
        server.serve()
