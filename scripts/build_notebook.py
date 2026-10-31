"""Generate an executable course notebook from recorded, real evaluation evidence."""
import json
import os
import sys
from pathlib import Path
import nbformat as nbf
from nbconvert import HTMLExporter
from nbclient import NotebookClient

root = Path(__file__).resolve().parents[1]
course = root / "course"
nb = nbf.v4.new_notebook()
nb.metadata = {"kernelspec": {"display_name": "BioLens Python", "language": "python", "name": "biolens"}, "language_info": {"name": "python", "version": "3.12"}}
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb.cells = [
md('''# BioLens：生物医学分析与可视化 Agent

课程：2026年秋季生物信息学 · Homework 3  
作者：请填写姓名、学号  
实现：Electron / React / Python / LangGraph；模型：通义千问 qwen3.7-flash

## 1. 研究目标与应用边界

BioLens帮助科研人员围绕本地数据和生物医学问题进行探索性分析、证据检索和可视化交付。用户以项目组织聊天，自主控制本地读取、外部检索以及聊天/报告模式。

本文验证三个生物医学问题：结核病血液转录组标志物、APOE与阿尔茨海默病风险、单细胞批次校正与过度校正。另用**合成表达数据**检验数据分析与报告流程；这些模拟值不能支持真实疾病结论。

本Notebook是课程报告；产品为Windows应用，核心代码在backend/biolens。Notebook直接调用相同核心分析模块，展示真实保存的Agent运行记录，避免重复实现。

默认重跑本Notebook不调用付费模型，而是读取随附的实际实验记录；重新运行实时实验见末尾说明。
'''),
code('''from pathlib import Path
import sys, json
ROOT = Path.cwd()
if not (ROOT / "backend").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "backend"))
import pandas as pd
from IPython.display import display, Markdown, Image
from biolens.analysis import analyze_expression
EVAL = ROOT / "course" / "evaluation"
records = {p.stem: json.loads(p.read_text("utf-8")) for p in EVAL.glob("*.json") if p.stem != "assessments"}
print("已加载真实实验记录：", len(records))
print("模型：", records["tb_signature_on_v2"]["model"])
'''),
md('''## 2. Agent设计与工作流

用户消息与权限 → 判断是否有明确检索请求 → 模型选择工具 → 执行并返回结果 → 模型继续决策或回答。实现使用LangGraph状态图，最多12轮工具决策，不是一次提示词调用。

工具包括项目文件列表、逐页PDF/文本读取、本地关键词检索、PubMed检索与摘要获取、确定性表达矩阵分析、报告导出，以及已有结果复用和图表样式修改。

- 权限开关由后端检查，不只依赖模型提示词。
- 外部检索开关开启，不意味着自动联网；当前消息需要有明确请求。
- 报告模式下内容不明确先问用户；用户决定HTML/PDF格式。
- 数据分析使用固定工具，不执行模型自由编写的代码。
- 文献结果包括PMID、标题、年份、摘要与来源地址；仅为摘要证据。
- 所有输出和工具记录均保存，便于复查；未检索到的PMID会标为未核验。

来源：PubMed E-utilities；https://www.ncbi.nlm.nih.gov/books/NBK25501/ 。模型使用阿里云百炼OpenAI兼容接口。
'''),
code('''from biolens.agent import TOOLS
display(pd.DataFrame([{"工具": t["function"]["name"], "用途": t["function"]["description"]} for t in TOOLS]))
'''),
md('''## 3. 真实问题测试：输入、工具、答案与判断

对每个问题分别关闭/开启外部检索。关闭时Agent应说明无法实时查询，而不是伪装为已经检索。该对照主要检验外部证据的可追溯性，不等于严格证明医学正确率提高。

以下判断是开发者对保存的摘要、工具记录和回答进行的初步核查，不是临床专家审阅，也不是大样本统计实验。
'''),
code('''rows = []
for name in ["tb_signature", "ad_apoe", "scrna_batch"]:
    for switch in ["off", "on"]:
        r = records[f"{name}_{switch}_v2"]
        calls = [e["payload"]["name"] for e in r["events"] if e["kind"] == "tool_start"]
        papers = [p for e in r["events"] if e["kind"] == "tool_end" and e["payload"]["name"] == "search_pubmed" and e["payload"].get("ok") for p in e["payload"]["result"].get("papers", [])]
        rows.append({"问题":name,"外部检索":switch,"状态":r["status"],"工具":", ".join(calls) or "无","返回文献":len(papers),"耗时秒":r["seconds"]})
display(pd.DataFrame(rows))
'''),
]
judgments = {
"tb_signature": "总体方向基本合理：回答列举转录组签名并说明不能直接替代常规诊断。但回答在PMID 20725040前添加了未由返回工具字段提供的作者名，不能视为已核验；蛋白组合与单细胞亚群也需要与血液转录组标志物严格区分。结论：部分正确，仍需逐项复核，不能因PMID存在就认定全文可靠。",
"ad_apoe": "抓住了风险关联不等于确定性诊断的区别，引用来自检索集合。回答中的风险百分比必须保留原始家族队列背景，不能推广成所有人群的绝对风险；机制和诊断叙述仍需全文及适用指南支持。结论：核心概念正确，但存在概括过宽和背景证据不足。",
"scrna_batch": "强调保留生物学差异、避免过度校正，列出了返回摘要中的方法并说明摘要局限。不过将ASW等概括为只衡量批次混合过于绝对，不同指标定义和使用方式需要区分；方法性能声明也需要独立验证。结论：有用但不完全正确，应将建议作为进一步核查线索。"
}
for name, label in [("tb_signature","问题一：结核病血液转录组标志物"),("ad_apoe","问题二：APOE与阿尔茨海默病风险"),("scrna_batch","问题三：单细胞批次校正")]:
    nb.cells += [md(f"### {label}"),code(f'''r = records["{name}_on_v2"]
display(Markdown("**输入问题：** " + r["request"]["prompt"]))
display(Markdown(r["answer"]))
papers = [p for e in r["events"] if e["kind"] == "tool_end" and e["payload"]["name"] == "search_pubmed" and e["payload"].get("ok") for p in e["payload"]["result"].get("papers", [])]
display(pd.DataFrame([{{"PMID":p["pmid"], "标题":p["title"], "年份":p["year"], "证据范围":p["evidence_scope"]}} for p in papers]))
'''),md("**正确性判断：** "+judgments[name])]
nb.cells += [
md('''## 4. 失败案例与修正

### 4.1 明确检索请求被误判

初版仅用模型返回的YES/NO决定检索权限。在结核病问题中，用户明确要求PubMed检索，开关也开启，但被判为不明确，最终没有工具调用；模型随后凭记忆输出了未核验的引用。

根因：权限意图识别被交给不稳定的模型输出，且引用缺少后置校验。修正：明显否定与明确检索请求使用规则优先处理，其他表达再分类；输出中不属于工具返回集合的PMID标记为未核验。复测确实调用PubMed。

修复不代表所有复杂语言都能正确分类，也不能保证真实PMID支持每个论断。此失败记录原样保留，没有替换为成功结果。
'''),
code('''before, after = records["tb_signature_on"], records["tb_signature_on_v2"]
for label, r in [("修正前", before), ("修正后", after)]:
    calls = [e["payload"]["name"] for e in r["events"] if e["kind"] == "tool_start"]
    print(label, "工具调用:", calls)
display(Markdown("**失败回答节选（不可当成可靠资料）：**\\n\\n" + before["answer"][-1100:]))
'''),
md('''### 4.2 数据不匹配：正确停止分析

故意将样本S12替换成WRONG_SAMPLE。Agent应报告不一致，不自行删除样本、替换文件或生成貌似完整的分析结论。
'''),
code('''r = records["sample_mismatch"]
display(Markdown(r["answer"]))
failures = [e["payload"] for e in r["events"] if e["kind"] == "tool_end" and not e["payload"].get("ok")]
display(failures)
'''),
md('''## 5. 本地数据分析与可视化复现

合成数据包含120个基因、12个样本。生成种子为20261026，前6个基因被人为增加组间偏移。仅验证软件计算与绘图，不是实验数据。

矩阵模拟已经处理的对数表达值，transform=none。PCA按基因中心化、不缩放；热图选高变异基因做行z-score。相关性使用Pearson。数值测试以NumPy独立计算作为基准。
'''),
code('''example = ROOT / "examples" / "expression-demo"
result = analyze_expression(str(example), True, ROOT / "artifacts" / "notebook-analysis", "expression.csv", "samples.csv", "group", genes=["STAT1", "GBP5"])
display(pd.DataFrame({"指标":["基因数","样本数","PC1解释方差","PC2解释方差"],"值":[result["genes"],result["samples"],*result["pca_explained_variance"]]}))
import plotly.io as pio
fig = pio.read_json(ROOT / "artifacts" / "notebook-analysis" / "pca.plotly.json")
from IPython.display import HTML
display(HTML(pio.to_html(fig, full_html=False, include_plotlyjs=True)))
'''),
md('''### Agent端到端报告交付

以下为真实模型调用读取、分析、报告工具的结果。HTML与PDF来自同一份分析结构，SVG/PNG与CSV可单独使用。点击产品“成果”可以查看或保存；课程报告本身与产品生成的科研报告是两种不同文件。
'''),
code('''r = records["report_both"]
display(Markdown(r["answer"]))
display(pd.DataFrame([{"工具": e["payload"]["name"], "成功":e["payload"]["ok"]} for e in r["events"] if e["kind"] == "tool_end"]))
'''),
md('''## 6. 权限和交互验证'''),
code('''for name in ["no_implicit_search","local_permission_off","local_permission_on","unclear_report"]:
    r = records[name]
    calls = [e["payload"]["name"] for e in r["events"] if e["kind"] == "tool_start"]
    display(Markdown("### " + name + "\\n工具：" + str(calls) + "\\n\\n" + r["answer"]))
'''),
md('''## 7. 工具是否提升可靠性？

本次三个问题的修正版对照中，开启检索后可获得可追溯的文献摘要与PMID；关闭时没有实时外部证据。工具显著增强了来源可检查性，固定分析工具也减少了临时生成代码带来的数值不确定性。

但“引用真实”不等于“解释正确”。以上人工检查仍发现概括过宽、文献条件未完整保留和引用身份以外的错误。因此本项目不能声称已经证明医学回答准确率普遍提高，也不能代替领域专家判断。测试样本仅三个问题，没有统计显著性结论。

## 8. 局限与改进

目前仅支持表格表达数据探索，不含正式差异表达、原始测序、OCR或任意代码执行。本地关键词检索有范围限制，PubMed只取得摘要。长会话只使用近期16条消息。PDF版式及静态图由实际导出测试检查，但复杂大数据仍需要更多案例。

后续可以增加更严格的逐论断证据检查、更多数据类型、分析工具、文献全文适配和实验评估。跨GPT/Codex产品对照尚未执行，参见comparison-protocol.md，不能用本项目模型的表现代替这些产品的真实结果。

## 9. 如何重新运行

使用项目setup脚本安装依赖，在设置中配置自己的模型密钥。执行 `node scripts/python.mjs scripts/evaluate.py` 和 `scripts/evaluate_revision.py` 可运行真实模型案例（会产生API费用；已有文件默认跳过）。执行 `scripts/live_report.py` 运行报告案例。密钥不随代码与Notebook分发。

## 10. 交付清单

- 本Notebook及其HTML导出，包含代码、实际运行结果、三个生物医学问题和失败案例。
- Windows客户端、项目源代码、README和示例数据。
- 10分钟汇报提纲，覆盖问题、Agent设计、演示、评估、失败与局限。

提交前填写个人信息，阅读上述判断并根据自己的理解完善；课程要求将带注释与运行结果的Notebook导出HTML，发送老师邮箱，结课后交完整版。视频不是文档中的必交项。
''')]
path = course / "BioLens-course-report.ipynb"
nbf.write(nb, path)
kernel_dir = root / ".local" / "jupyter" / "kernels" / "biolens"
kernel_dir.mkdir(parents=True, exist_ok=True)
(kernel_dir / "kernel.json").write_text(json.dumps({"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"], "display_name": "BioLens Python", "language": "python", "env": {"PYTHONPATH": os.environ.get("PYTHONPATH", ""), "PYTHONUTF8": "1", "BIOLENS_DATA": os.environ.get("BIOLENS_DATA", "")}}), "utf-8")
os.environ["JUPYTER_PATH"] = os.pathsep.join([str(root / ".local" / "jupyter"), str(root / ".local" / "pylibs" / "share" / "jupyter")])
client = NotebookClient(nb, timeout=180, kernel_name="biolens", resources={"metadata": {"path": str(root)}})
client.execute()
nbf.write(nb, path)
exporter = HTMLExporter()
body, _ = exporter.from_notebook_node(nb)
(course / "BioLens-course-report.html").write_text(body, "utf-8")
print("Executed Notebook and HTML generated:", len(nb.cells), "cells")
