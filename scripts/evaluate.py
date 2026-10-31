"""Live evaluations. No answers are fabricated; persist complete tool evidence."""
import asyncio
import json
import time
from pathlib import Path
from biolens import store
from biolens.agent import Runner
from biolens.schemas import TurnIn
from biolens.config import read_settings

root = Path(__file__).resolve().parents[1]
out = root / "course" / "evaluation"
out.mkdir(parents=True, exist_ok=True)
questions = [
    ("tb_signature", "请在PubMed检索结核病血液转录组诊断标志物的研究。用不超过500字回答：有哪些候选基因或特征？这些证据是否足以支持直接临床诊断？请给出可核查引用。"),
    ("ad_apoe", "请在PubMed检索APOE与阿尔茨海默病风险的研究。用不超过500字解释遗传风险关联与确定性诊断之间的区别，并给出可核查引用。"),
    ("scrna_batch", "请在PubMed检索单细胞RNA测序批次校正与过度校正的研究。用不超过500字说明如何避免把真实生物差异消除，给出可核查引用和证据局限。"),
]

async def case(name, request):
    target = out / f"{name}.json"
    if target.exists():
        print("Already recorded:", name, flush=True)
        return
    project = {"id": store.uid(), "name": "课程验证", "path": str(root / "examples" / "expression-demo")}
    chat, run_id = store.uid(), store.uid()
    store.execute("INSERT INTO projects VALUES(?,?,?,?)", (project["id"], project["name"], project["path"], store.now()))
    store.execute("INSERT INTO chats VALUES(?,?,?,?)", (chat, project["id"], name, store.now()))
    store.message(chat, "user", request.prompt)
    store.execute("INSERT INTO runs VALUES(?,?,?,?,?)", (run_id, chat, request.model_dump_json(), "running", store.now()))
    start = time.monotonic()
    await Runner(run_id, chat, project, request).run()
    events = [{"kind": r["kind"], "payload": json.loads(r["payload"])} for r in store.rows("SELECT * FROM events WHERE run_id=? ORDER BY id", (run_id,))]
    answers = store.rows("SELECT content FROM messages WHERE chat_id=? AND role='assistant' ORDER BY rowid", (chat,))
    result = {"case": name, "run_id": run_id, "timestamp": store.now(), "model": read_settings()["model"], "request": request.model_dump(), "seconds": round(time.monotonic()-start, 2),
              "status": store.rows("SELECT status FROM runs WHERE id=?", (run_id,))[0]["status"], "answer": "\n".join(a["content"] for a in answers), "events": events}
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(name, result["status"], result["seconds"], "tools:", [e["payload"]["name"] for e in events if e["kind"] == "tool_start"], flush=True)

async def main():
    store.init()
    for name, prompt in questions:
        await case(name + "_off", TurnIn(prompt=prompt, external=False))
        await case(name + "_on", TurnIn(prompt=prompt, external=True))
    await case("no_implicit_search", TurnIn(prompt="用一句话解释NMF，不需要查资料。", external=True))
    await case("local_permission_off", TurnIn(prompt="请读取本地README.md，告诉我数据是否为真实患者数据。", local=False))
    await case("local_permission_on", TurnIn(prompt="请读取本地README.md，告诉我数据是否为真实患者数据。", local=True))
    await case("unclear_report", TurnIn(prompt="帮我做一个可视化报告。", local=False, mode="report"))
    await case("sample_mismatch", TurnIn(prompt="请用expression.csv和samples-mismatch.csv按group分析表达数据，行是基因列是样本，数据已处理不再变换。检查样本是否匹配；不允许自行修复、删除样本或换文件。", local=True))

if __name__ == "__main__":
    asyncio.run(main())
