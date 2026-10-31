import asyncio
from evaluate import case, store
from biolens.schemas import TurnIn

async def main():
    store.init()
    await case("report_both", TurnIn(prompt="请先读README.md，然后用expression.csv和samples.csv按group分组，transform=none，展示PCA、样本相关性、热图，以及STAT1和GBP5的表达，生成HTML和PDF报告。强调这是合成数据，不做疾病结论。不需要外部检索。", local=True, mode="report", report_format="both"))

asyncio.run(main())
