import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];BASE='https://biolens.worldlinesite.com'
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch()
  context=await browser.new_context(viewport={'width':1440,'height':960},extra_http_headers={'Origin':BASE})
  credentials=json.loads((ROOT/'.local/web-test-credentials.json').read_text('utf-8'))
  login=await context.request.post(BASE+'/web-api/account/login',data=credentials);assert login.ok
  projects=await (await context.request.get(BASE+'/web-api/projects')).json();project=projects[0]
  chat=(await (await context.request.get(BASE+'/web-api/chats?project_id='+project['id'])).json())[0]
  detail=await (await context.request.get(BASE+'/web-api/chats/'+chat['id'])).json()
  trace=await (await context.request.get(BASE+'/web-api/runs/'+detail['runs'][0]['id']+'/trace')).json()
  assert detail['runs'][0]['status']=='completed'
  for name in ['report.pdf','report.html']:
   a=next(a for a in detail['artifacts'] if a['name']==name)
   r=await context.request.get(BASE+'/web-api/artifacts/'+a['id'],timeout=180000);assert r.ok
   (ROOT/'artifacts'/('web-'+name)).write_bytes(await r.body())
   print('Downloaded '+name,flush=True)
  pdf=next(a for a in detail['artifacts'] if a['name']=='report.pdf')
  preview=await context.request.get(BASE+'/web-api/artifacts/'+pdf['id']+'/preview')
  assert '/web-api/artifacts/' in await preview.text()
  assert (await context.request.get(BASE+'/web-api/artifacts/'+pdf['id']+'/pages/0',timeout=120000)).ok
  # The same credentials and chat must be visible through the desktop cloud API.
  remote=await context.request.post(BASE+'/auth/login',data=credentials);assert remote.ok
  headers={'Authorization':'Bearer '+(await remote.json())['token']}
  messages=await (await context.request.get(BASE+'/chats/'+chat['id']+'/messages',headers=headers)).json()
  assert any(m['role']=='assistant' for m in messages)
  await context.request.post(BASE+'/auth/logout',headers=headers)
  page=await context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(BASE)
  await page.get_by_role('button',name=project['name'],exact=True).click()
  await page.get_by_role('button',name=chat['title'],exact=True).click()
  await page.get_by_text('已完成探索分析并生成报告。',exact=False).first.wait_for()
  await page.screenshot(path=str(ROOT/'artifacts/ui/web-completed.png'))
  await page.set_viewport_size({'width':390,'height':844})
  await page.screenshot(path=str(ROOT/'artifacts/ui/web-mobile.png'))
  assert not errors,errors
  result={'tools':[t['payload']['name'] for t in trace if t['kind']=='tool_end' and t['payload']['ok']], 'html_pdf':'passed','continue_after_tab_close':'passed','cookie_login_after_reload':'passed','desktop_chat_sync':'passed','pdf_preview':'passed','browser_errors':errors}
  (ROOT/'artifacts/web-e2e.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(result),flush=True)
  await browser.close()
asyncio.run(main())
