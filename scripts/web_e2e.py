"""Real browser verification of the deployed web app; no provider or API mocks."""
import asyncio,json,secrets,uuid
from pathlib import Path
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
BASE='https://biolens.worldlinesite.com'
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch()
  context=await browser.new_context(viewport={'width':1440,'height':960},extra_http_headers={'Origin':BASE})
  page=await context.new_page();errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(BASE)
  credentials_file=ROOT/'.local/web-test-credentials.json'
  registering=not credentials_file.exists()
  credentials=json.loads(credentials_file.read_text('utf-8')) if not registering else {'username':'verify_'+uuid.uuid4().hex[:10],'password':secrets.token_urlsafe(24)}
  if registering:await page.get_by_role('button',name='还没有账号？注册').click()
  username=credentials['username'];password=credentials['password'];project_name='网页验证-'+uuid.uuid4().hex[:6]
  await page.get_by_label('用户名',exact=True).fill(username)
  await page.get_by_label('密码',exact=True).fill(password)
  await page.get_by_role('button',name='注册并登录' if registering else '登录',exact=True).click()
  await page.get_by_role('button',name='创建项目',exact=True).wait_for(timeout=30000)
  credentials_file.write_text(json.dumps(credentials),'utf-8')
  account=await (await context.request.get(BASE+'/web-api/account')).json()
  file=ROOT/'.local/cloud-test-users.json';users=json.loads(file.read_text('utf-8')) if file.exists() else []
  
  if account['user'] not in users:users.append(account['user']);file.write_text(json.dumps(users),'utf-8')
  await page.get_by_role('button',name='创建项目',exact=True).click()
  await page.get_by_label('项目名称').fill(project_name)
  await page.get_by_role('dialog').get_by_role('button',name='创建项目',exact=True).click()
  await page.get_by_role('button',name='项目文件',exact=True).click()
  await page.get_by_label('上传项目文件').set_input_files([str(ROOT/'examples/expression-demo'/n) for n in ['README.md','expression.csv','samples.csv']])
  await page.get_by_text('上传完成。开启“项目资料”后，Agent 才能读取。',exact=True).wait_for(timeout=30000)
  await page.screenshot(path=str(ROOT/'artifacts/ui/web-files.png'))
  await page.get_by_role('button',name='关闭项目文件').click()
  await page.get_by_role('switch',name='项目资料').click()
  await expect(page.get_by_role('switch',name='项目资料')).to_have_attribute('aria-checked','true')
  await page.get_by_role('button',name='可视化报告',exact=True).click()
  await page.get_by_label('报告格式').select_option('both')
  await page.get_by_label('消息',exact=True).fill('读取README.md，用expression.csv和samples.csv做探索分析，group分组，transform=none，展示STAT1和GBP5，生成HTML与PDF报告。注明是合成演示数据，不作疾病结论。')
  async with page.expect_response(lambda r:'/turns' in r.url and r.request.method=='POST') as response:
   await page.get_by_role('button',name='发送',exact=True).click()
  r=await response.value;assert r.ok,await r.text();run=(await r.json())['run_id']
  await page.close()
  for _ in range(180):
   trace=await (await context.request.get(BASE+'/web-api/runs/'+run+'/trace')).json()
   if any(t['kind']=='done' for t in trace):break
   await asyncio.sleep(2)
  assert any(t['kind']=='done' and t['payload']['status']=='completed' for t in trace),trace[-3:]
  tools=[t['payload']['name'] for t in trace if t['kind']=='tool_end' and t['payload']['ok']]
  assert 'create_report' in tools,trace[-5:]
  project=(await (await context.request.get(BASE+'/web-api/projects')).json())[0]
  chat=(await (await context.request.get(BASE+'/web-api/chats?project_id='+project['id'])).json())[0]
  detail=await (await context.request.get(BASE+'/web-api/chats/'+chat['id'])).json()
  pdf=next(a for a in detail['artifacts'] if a['name']=='report.pdf')
  html=next(a for a in detail['artifacts'] if a['name']=='report.html')
  for a in [pdf,html]:
   result=await context.request.get(BASE+'/web-api/artifacts/'+a['id'],timeout=180000);assert result.ok
   (ROOT/'artifacts'/('web-'+a['name'])).write_bytes(await result.body())
  assert (ROOT/'artifacts/web-report.pdf').read_bytes().startswith(b'%PDF')
  preview=await context.request.get(BASE+'/web-api/artifacts/'+pdf['id']+'/preview')
  assert '/web-api/artifacts/' in await preview.text()
  assert (await context.request.get(BASE+'/web-api/artifacts/'+pdf['id']+'/pages/0')).ok
  page=await context.new_page();await page.goto(BASE)
  await page.get_by_role('button',name=project_name,exact=True).click()
  await page.get_by_role('button',name=chat['title'],exact=True).click()
  await page.screenshot(path=str(ROOT/'artifacts/ui/web-completed.png'))
  await page.set_viewport_size({'width':390,'height':844})
  await page.screenshot(path=str(ROOT/'artifacts/ui/web-mobile.png'))
  assert not errors,errors
  result={'tools':tools,'html_pdf':'passed','continue_after_tab_close':'passed','cookie_login_after_reload':'passed','pdf_preview':'passed','browser_errors':errors}
  (ROOT/'artifacts/web-e2e.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
  print(json.dumps(result),flush=True)
  await browser.close()
asyncio.run(main())
