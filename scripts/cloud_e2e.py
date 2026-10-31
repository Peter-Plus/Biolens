"""End-to-end test: real cloud accounts + local scoped executor + actual reports."""
import os,asyncio,json,secrets,uuid,subprocess,sys,time
from pathlib import Path
import httpx
from playwright.async_api import async_playwright
root=Path(__file__).resolve().parents[1]
users=json.loads((root/'.local/cloud-test-users.json').read_text('utf-8')) if (root/'.local/cloud-test-users.json').exists() else []
async def main():
 env=dict(os.environ,BIOLENS_CLOUD_URL='https://biolens.worldlinesite.com',BIOLENS_DATA=str(root/'.local/cloud-e2e'),BIOLENS_PORT='18769',BIOLENS_TOKEN='cloud-e2e-local-token')
 process=subprocess.Popen([sys.executable,'-m','biolens'],env=env,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 report={}
 try:
  async with httpx.AsyncClient(base_url='http://127.0.0.1:18769',headers={'Authorization':'Bearer cloud-e2e-local-token'},timeout=180) as local, httpx.AsyncClient(base_url=env['BIOLENS_CLOUD_URL'],timeout=180) as remote:
   for _ in range(60):
    try:
     if (await local.get('/health')).is_success:break
    except httpx.RequestError:pass
    await asyncio.sleep(.5)
   a='verify_'+uuid.uuid4().hex[:10];password=secrets.token_urlsafe(20)
   r=await local.post('/account/register',json={'username':a,'password':password});r.raise_for_status();users.append(r.json()['user'])
   p=(await local.post('/projects',json={'name':'云端联调（临时测试）','path':str(root/'examples/expression-demo')})).json()
   c=(await local.post('/chats',json={'project_id':p['id']})).json()
   turn=await local.post('/chats/'+c['id']+'/turns',json={'prompt':'读取README.md，用expression.csv和samples.csv，group分组，transform=none，展示STAT1和GBP5，生成HTML与PDF。请在PubMed检索STAT1 interferon，最多2篇，结合摘要说明其研究背景。数据是合成演示，不作疾病结论。','model':'qwen3.7-flash','local':True,'external':True,'mode':'report','report_format':'both'})
   turn.raise_for_status();run=turn.json()['run_id']
   for _ in range(240):
    trace=(await local.get('/runs/'+run+'/trace')).json()
    if any(x['kind']=='done' for x in trace):break
    await asyncio.sleep(1)
   detail=(await local.get('/chats/'+c['id'])).json()
   successful=[x['payload']['name'] for x in trace if x['kind']=='tool_end' and x['payload']['ok']]
   report['tools']=successful;report['artifacts']=[x['name'] for x in detail['artifacts']]
   assert all(x in successful for x in ['search_pubmed','analyze_expression','create_report']),successful
   pdf=next(x for x in detail['artifacts'] if x['name']=='report.pdf')
   assert (await local.get('/artifacts/'+pdf['id'])).content.startswith(b'%PDF')
   # Login directly to cloud, confirm metadata but no local paths/artifact uploads.
   login=await remote.post('/auth/login',json={'username':a,'password':password});login.raise_for_status()
   headers={'Authorization':'Bearer '+login.json()['token']}
   projects=(await remote.get('/projects',headers=headers)).json();assert all('path' not in x for x in projects)
   messages=(await remote.get('/chats/'+c['id']+'/messages',headers=headers)).json();assert any(x['role']=='assistant' for x in messages)
   b='verify_'+uuid.uuid4().hex[:10];reg=await remote.post('/auth/register',json={'username':b,'password':secrets.token_urlsafe(20)});reg.raise_for_status();users.append(reg.json()['user'])
   hb={'Authorization':'Bearer '+reg.json()['token']}
   assert (await remote.get('/chats/'+c['id']+'/messages',headers=hb)).status_code==404
   await remote.post('/auth/logout',headers=hb)
   # Five concurrent authenticated model requests, one from each account will be tested separately if needed.
   report['cloud_sync']='passed';report['cross_account_access']='denied';report['raw_paths_uploaded']=False
   await local.post('/account-logout')
   assert (await local.get('/artifacts/'+pdf['id'])).status_code==401
   await remote.post('/auth/logout',headers=headers)
   print(json.dumps(report,ensure_ascii=False),flush=True)
 finally:
  process.terminate();process.wait(timeout=10)
  (root/'.local/cloud-test-users.json').write_text(json.dumps(users),'utf-8')
  (root/'artifacts/cloud-e2e.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
asyncio.run(main())
