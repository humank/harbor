"""Underwriting Risk Agent — Strands Agent (hybrid: formula + LLM interpretation)."""

import json
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

from config import AGENT_PORTS, BEDROCK_MODEL, USE_BEDROCK
from tools.risk_scoring import assess


@tool
def calculate_risk_score(age: int = 30, height_cm: float = 170, weight_kg: float = 65,
                         occupation_class: int = 1, smoking_status: str = "never",
                         conditions: str = "none", family_history: str = "none") -> str:
    """計算核保風險分數。根據年齡、身高體重、職業、吸菸、既往症、家族史計算加權風險評分。"""
    cond_list = [c.strip() for c in conditions.split(",")]
    fam_list = [f.strip() for f in family_history.split(",")]
    result = assess(age, height_cm, weight_kg, occupation_class, smoking_status, cond_list, fam_list)
    return json.dumps(result, ensure_ascii=False)


SYSTEM_PROMPT = """你是核保風險評估專家。

工作流程：
1. 呼叫 calculate_risk_score tool 取得精確的風險評分
2. 根據評分結果，用專業但易懂的語言解讀：
   - 哪些因子是主要風險來源
   - 預期的核保結果（標準體/加費/拒保）
   - 改善建議（如果有的話）
3. 一定要附上免責聲明：此為預評估，非正式核保結果

重要：風險分數必須由 tool 計算，你不要自己算。你的角色是解讀結果。
回覆時先列出 JSON 格式的評分結果，再用中文解讀。"""

agent_kwargs = {"name": "風險預評估 Agent", "description": "根據被保險人健康、職業、生活習慣評估核保風險等級",
                "system_prompt": SYSTEM_PROMPT, "tools": [calculate_risk_score]}
if USE_BEDROCK:
    agent_kwargs["model"] = BEDROCK_MODEL

agent = Agent(**agent_kwargs)

if __name__ == "__main__":
    server = A2AServer(agent=agent, host="0.0.0.0", port=AGENT_PORTS["underwriting_risk"])
    server.serve()
