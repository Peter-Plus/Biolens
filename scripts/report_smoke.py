import asyncio
import json
from pathlib import Path
from biolens.analysis import analyze_expression
from biolens.reports import export_report

root = Path(__file__).resolve().parents[1]
out = root / "artifacts" / "report-smoke"

async def main():
    result = analyze_expression(str(root / "examples" / "expression-demo"), True, out, "expression.csv", "samples.csv", "group", genes=["STAT1", "GBP5"])
    files = await export_report(out, "合成表达数据：分析与可视化示例", [
        {"heading": "研究问题与数据边界", "body": "检查演示组之间的整体表达模式，并展示指定基因的表达分布。这是人工合成数据，用于软件验证，不是真实患者研究。"},
        {"heading": "方法与观察", "body": f"使用12个样本与120个基因，输入模拟已经处理的对数表达量，不再次取对数。PCA第一主成分解释方差为{result['pca_explained_variance'][0]:.1%}。前6个基因被人为加入组间偏移，因此组间差异属于数据生成机制，不能推广为疾病发现。"},
        {"heading": "局限", "body": "没有做正式差异表达检验，未推断因果关系。应在真实数据及适当实验设计下重新验证。"}
    ], [], result, "both")
    import fitz
    doc = fitz.open(out / "report.pdf")
    for i, page in enumerate(doc):
        page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2)).save(out / f"page-{i+1}.png")
    assert "合成" in ''.join(p.get_text() for p in doc)
    print(json.dumps({"files": [p.name for p in files], "pdf_pages": len(doc)}, ensure_ascii=False))

asyncio.run(main())
