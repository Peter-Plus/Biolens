import asyncio,json,httpx
from pathlib import Path
from biolens.config import read_settings
MODELS=['qwen3.6-flash','qwen3.7-flash','qwen3.7-plus','qwen3.8-flash','qwen3.7-max','qwen3.8-max']
async def main():
 c=read_settings()
 async with httpx.AsyncClient(timeout=100) as client:
  async def test(model):
   messages=[{'role':'user','content':'必须调用 read_demo 工具读取样本数，再根据工具返回值回答样本数，不要猜测。'}]
   tool={'type':'function','function':{'name':'read_demo','description':'读取演示数据的样本数','parameters':{'type':'object','properties':{},'additionalProperties':False}}}
   body={'model':model,'messages':messages,'tools':[tool],'temperature':.2,'enable_thinking':False,'max_tokens':160}
   try:
    r=await client.post(c['base_url'].rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+c['api_key']},json=body)
    result={'model':model,'status':r.status_code}
    if r.is_success:
     msg=r.json()['choices'][0]['message'];calls=msg.get('tool_calls') or []
     result['tool_call']=bool(calls) and all(x['function']['name']=='read_demo' for x in calls)
     if result['tool_call']:
      messages.append({'role':'assistant','content':msg.get('content') or '', 'tool_calls':calls})
      for call in calls: messages.append({'role':'tool','tool_call_id':call['id'],'content':'{"sample_count":12}'})
      r=await client.post(c['base_url'].rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+c['api_key']},json=body)
      result['return_status']=r.status_code
      result['roundtrip']=r.is_success and '12' in (r.json()['choices'][0]['message'].get('content') or '')
    print(json.dumps(result),flush=True);return result
   except Exception as e:
    result={'model':model,'error_type':type(e).__name__};print(json.dumps(result),flush=True);return result
  results=await asyncio.gather(*(test(m) for m in MODELS))
 Path('artifacts/model-catalog-check.json').write_text(json.dumps(results,indent=2),'utf-8')
asyncio.run(main())
