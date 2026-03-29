"""Premium Calculator Agent — Strands A2AServer, deterministic (no LLM)."""

import json
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

from config import AGENT_PORTS
from tools.premium_calc import calc_batch


@tool
def calculate_premium(items_json: str) -> str:
    """試算保費。傳入 JSON 陣列，每個元素含 product_id, age, risk_class。回傳各商品保費明細。"""
    items = json.loads(items_json)
    result = calc_batch(items)
    return json.dumps(result, ensure_ascii=False)


agent = Agent(
    name="保費試算 Agent",
    description="根據商品、年齡、風險等級計算保費",
    system_prompt="你是保費試算助手。直接呼叫 tool 回傳結果，不要加入自己的解讀。用 JSON 格式回傳。",
    tools=[calculate_premium],
    callback_handler=None,
)

if __name__ == "__main__":
    server = A2AServer(agent=agent, host="0.0.0.0", port=AGENT_PORTS["premium_calculator"])
    server.serve()
