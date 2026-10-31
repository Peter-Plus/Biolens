import asyncio
import json
import time
from pathlib import Path
from biolens import store
from biolens.agent import Runner
from biolens.schemas import TurnIn
from biolens.config import ARTIFACT_DIR

root=Path(__file__).resolve().parents[1]

async def main():
    store.init()
    original=json.loads((root/'course/evaluation/report_both.json').read_text('utf-8'))
    chat_id=store.rows('SELECT chat_id FROM runs WHERE id=?',(original['run_id'],))[0]['chat_id']
    project=store.rows('SELECT p.* FROM projects p JOIN chats c ON p.id=c.project_id WHERE c.id=?',(chat_id,))[0]
    request=TurnIn(prompt='请复用刚才的分析结果，把PCA标题改为“样本表达概览”，两个组的颜色改为#147D79和#3E82BC。不重新读取项目或计算数据，生成新的HTML和PDF报告，并保留原报告。',mode='report',report_format='both')
    run_id=store.uid()
    store.message(chat_id,'user',request.prompt)
    store.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(run_id,chat_id,request.model_dump_json(),'running',store.now()))
    await Runner(run_id,chat_id,project,request).run()
    events=[{'kind':e['kind'],'payload':json.loads(e['payload'])} for e in store.rows('SELECT * FROM events WHERE run_id=? ORDER BY id',(run_id,))]
    result={'case':'report_modify','run_id':run_id,'status':store.rows('SELECT status FROM runs WHERE id=?',(run_id,))[0]['status'],'request':request.model_dump(),'events':events,'answer':store.rows("SELECT content FROM messages WHERE chat_id=? AND role='assistant' ORDER BY rowid DESC LIMIT 1",(chat_id,))[0]['content']}
    original_dir=ARTIFACT_DIR/original['run_id']
    revised_dir=ARTIFACT_DIR/run_id
    assert (original_dir/'report.pdf').exists()
    assert (revised_dir/'report.pdf').exists()
    assert (original_dir/'pca_scores.csv').read_bytes()==(revised_dir/'pca_scores.csv').read_bytes()
    assert json.loads((revised_dir/'pca.plotly.json').read_text('utf-8'))['layout']['title']['text']=='样本表达概览'
    (root/'course/evaluation/report_modify.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print('Report revision, unchanged data, original retained: PASS')
asyncio.run(main())
