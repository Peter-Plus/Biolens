import asyncio,json,re
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];BASE='https://biolens.worldlinesite.com'
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch();context=await browser.new_context(viewport={'width':1440,'height':960},extra_http_headers={'Origin':BASE})
  assert (await context.request.post(BASE+'/web-api/account/login',data=json.loads((ROOT/'.local/web-test-credentials.json').read_text('utf-8')))).ok
  print('Login ready',flush=True)
  project=(await (await context.request.get(BASE+'/web-api/projects')).json())[0]
  chat=(await (await context.request.get(BASE+'/web-api/chats?project_id='+project['id'])).json())[0]
  page=await context.new_page();page.on('requestfailed',lambda r:print('Failed request',r.url,r.failure,flush=True));page.on('request',lambda r:print('Requested',r.url,flush=True) if '/artifacts/' in r.url else None);page.on('response',lambda r:print('Artifact HTTP',r.status,flush=True) if '/artifacts/' in r.url else None);page.on('pageerror',lambda e:print('Frame error',str(e)[:400],flush=True));await page.goto(BASE);print('Page opened',flush=True)
  await page.get_by_role('button',name=project['name'],exact=True).click();await page.get_by_role('button',name=chat['title'],exact=True).click()
  print('Chat opened',flush=True)
  await page.get_by_role('button',name=re.compile('^成果')).click()
  await page.get_by_role('button',name='HTML report.html',exact=True).click()
  print('HTML requested',await page.locator('iframe').get_attribute('src'),flush=True)
  await page.screenshot(path=str(ROOT/'artifacts/ui/web-preview-debug.png'),timeout=10000)
  frame=page.frame_locator('iframe[title="report.html"]')
  await asyncio.sleep(5)
  print('Frame text', (await frame.locator('body').inner_text(timeout=10000))[:300],flush=True)
  await frame.locator('.js-plotly-plot').first.wait_for(timeout=60000)
  assert await frame.locator('.js-plotly-plot').count()==6
  print('HTML charts ready',flush=True)
  await page.screenshot(path=str(ROOT/'artifacts/ui/web-html-preview.png'),timeout=20000)
  await page.get_by_role('button',name='返回文件列表').click()
  await page.get_by_role('button',name='PDF report.pdf',exact=True).click()
  await page.frame_locator('iframe[title="report.pdf"]').locator('img').first.wait_for(timeout=30000)
  await page.screenshot(path=str(ROOT/'artifacts/ui/web-pdf-preview.png'))
  print('HTML interactive charts and PDF iframe previews: PASS',flush=True)
  await browser.close()
asyncio.run(asyncio.wait_for(main(),240))
