import asyncio,json
from pathlib import Path
from biolens import store
from biolens.agent import Runner
from biolens.schemas import TurnIn
async def main():
 store.init();chat=store.uid();run=store.uid()
 prompt='请读README.md，用expression.csv和samples.csv分析。group分组，batch_column=library_type，reference_group=untreated，transform=none。展示FBgn0000008和FBgn0000014，生成HTML和PDF。分析处理状态和测序类型对PCA的描述性关联，不做显著性检验。'
 request=TurnIn(prompt=prompt,model='qwen3.8-max',local=True,mode='report',report_format='both')
 store.message(chat,'user',prompt);store.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(run,chat,request.model_dump_json(),'running',store.now()))
 await Runner(run,chat,{'name':'Pasilla真实数据验证','path':str(Path('examples/pasilla').resolve())},request).run()
 events=store.rows('SELECT kind,payload FROM events WHERE run_id=?',(run,));out=Path('artifacts/visual-iterations/agent-check.json');out.write_text(json.dumps(events,ensure_ascii=False,indent=2),'utf-8')
 successes=[]
 for e in events:
  p=json.loads(e['payload'])
  if e['kind']=='tool_end':
   print(p['name'],p['ok']);successes.append(p['name'] if p['ok'] else '')
 assert 'analyze_expression' in successes and 'create_report' in successes
 print('Real Qwen agent report PASS',run)
asyncio.run(main())
