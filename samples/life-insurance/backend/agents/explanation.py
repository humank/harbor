"""Explanation Agent — Strands Agent (pure LLM, no tools)."""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from strands import Agent
from strands.multiagent.a2a import A2AServer

from config import AGENT_PORTS, BEDROCK_MODEL_LIGHT, USE_BEDROCK

SYSTEM_PROMPT = """你是保險知識專家，專門用白話文解釋保險術語和條款。

規則：
- 用台灣的保險用語和繁體中文
- 舉生活化的例子幫助理解
- 不要給投保建議，只解釋概念
- 如果不確定，說「建議諮詢保險業務員」

你可以解釋的主題包括：
- 險種差異（壽險、醫療險、意外險、年金險等）
- 保險術語（實支實付、等待期、豁免保費、保單借款等）
- 核保概念（標準體、加費、除外、拒保等）
- 理賠流程和注意事項"""

agent_kwargs = {"name": "保險知識 Agent", "description": "用白話文解釋保險術語和條款",
                "system_prompt": SYSTEM_PROMPT, "tools": []}
if USE_BEDROCK:
    agent_kwargs["model"] = BEDROCK_MODEL_LIGHT

agent = Agent(**agent_kwargs)

if __name__ == "__main__":
    server = A2AServer(agent=agent, host="0.0.0.0", port=AGENT_PORTS["explanation"])
    server.serve()
