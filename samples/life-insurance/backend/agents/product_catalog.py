"""Product Catalog Agent — Strands A2AServer, deterministic (no LLM)."""

import json
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

from config import AGENT_PORTS, USE_BEDROCK
from tools.product_search import search, compare


@tool
def search_products(age: int = 0, types: str = "", budget_monthly: int = 0, providers: str = "cathay,fubon") -> str:
    """搜尋保險商品。根據年齡、險種類型（逗號分隔）、月預算篩選國泰/富邦的商品。"""
    type_list = [t.strip() for t in types.split(",") if t.strip()] if types else []
    provider_list = [p.strip() for p in providers.split(",")]
    result = search(age, type_list, budget_monthly, provider_list)
    return json.dumps(result, ensure_ascii=False)


@tool
def compare_products(product_ids: str) -> str:
    """比較指定商品。傳入逗號分隔的 product_id 清單。"""
    ids = [pid.strip() for pid in product_ids.split(",")]
    result = compare(ids)
    return json.dumps(result, ensure_ascii=False)


agent = Agent(
    name="商品目錄 Agent",
    description="查詢國泰/富邦壽險商品目錄，依客戶需求篩選推薦與比較",
    system_prompt="你是商品查詢助手。直接呼叫 tool 回傳結果，不要加入自己的解讀。用 JSON 格式回傳。",
    tools=[search_products, compare_products],
    callback_handler=None,
)

if __name__ == "__main__":
    server = A2AServer(agent=agent, host="0.0.0.0", port=AGENT_PORTS["product_catalog"])
    server.serve()
