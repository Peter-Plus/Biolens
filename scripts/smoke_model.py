import asyncio
from biolens.agent import completion, explicit_search_request
from biolens.pubmed import search_pubmed

async def main():
    response = await completion([{"role": "user", "content": "只回答：BioLens连接成功"}])
    print("Model:", response.get("content"))
    tool = {"type": "function", "function": {"name": "probe", "description": "工具连通性测试", "parameters": {"type": "object", "properties": {}, "required": []}}}
    response = await completion([{"role": "user", "content": "请调用probe工具。"}], [tool])
    print("Tool calling:", bool(response.get("tool_calls")))
    print("No-search intent:", await explicit_search_request("解释一下NMF，不要检索"))
    print("Search intent:", await explicit_search_request("请在PubMed检索结核病的血液转录组标志物"))
    result = await search_pubmed("tuberculosis blood transcriptomic signature", 2)
    print("PubMed:", result["total"], [p["pmid"] for p in result["papers"]])

asyncio.run(main())
