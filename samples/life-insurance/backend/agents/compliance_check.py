"""Compliance Check Agent — Strands A2AServer, deterministic (no LLM)."""

import json
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

from config import AGENT_PORTS
from tools.compliance_rules import check


@tool
def check_compliance(age: int = 30, product_category: str = "醫療險", sum_insured: int = 0,
                     annual_income: int = 0, annual_premium_total: int = 0) -> str:
    """檢查投保資格。根據年齡、商品類型、保額、收入檢查法規限制。"""
    result = check(age, product_category, sum_insured,
                   annual_income or None, annual_premium_total or None)
    return json.dumps(result, ensure_ascii=False)


agent = Agent(
    name="合規檢查 Agent",
    description="檢查年齡、保額、財力等投保資格限制",
    system_prompt="你是合規檢查助手。直接呼叫 tool 回傳結果，不要加入自己的解讀。用 JSON 格式回傳。",
    tools=[check_compliance],
    callback_handler=None,
)

if __name__ == "__main__":
    server = A2AServer(agent=agent, host="0.0.0.0", port=AGENT_PORTS["compliance_check"])
    server.serve()
