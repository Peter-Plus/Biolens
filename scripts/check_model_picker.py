import asyncio,json,subprocess
from pathlib import Path
from playwright.async_api import async_playwright
from biolens.models import MODELS, DEFAULT_MODEL
root=Path.cwd()
async def main():
 vite=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5178'],creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL)
 try:
  async with async_playwright() as pw:
   browser=await pw.chromium.launch()
   page=await browser.new_page(viewport={'width':1380,'height':900})
   names=['pca.html','correlation.html','report.html','report.pdf','pca.png','heatmap.png','pca.svg','heatmap.svg','pca_scores.csv','analysis.json']
   artifacts=[{'id':str(i),'run_id':'r1','name':n,'kind':n.split('.')[-1]} for i,n in enumerate(names)]
   async def route(r):
    path=r.request.url.split('8765')[-1].split('?')[0]
    if path=='/chats/c/turns':
     assert r.request.post_data_json['model']=='qwen3.8-max'
     await r.fulfill(json={'run_id':'test-run'});return
    value={'/models':{'models':MODELS,'default_model':DEFAULT_MODEL},'/projects':[{'id':'p','name':'表达数据演示','path':'demo'}],'/settings':{'model':'qwen3.7-flash','has_key':True},'/chats':[{'id':'c','title':'报告示例','project_id':'p'}],'/chats/c':{'messages':[{'id':'m','role':'assistant','content':'报告已生成，请在成果中查看。'}],'artifacts':artifacts,'runs':[]}}.get(path,{})
    await r.fulfill(json=value)
   await page.route('http://127.0.0.1:8765/**',route)
   for _ in range(30):
    try:
     await page.goto('http://127.0.0.1:5178');break
    except Exception: await asyncio.sleep(.5)
   await page.get_by_role('button',name='表达数据演示',exact=True).click()
   await page.get_by_role('button',name='报告示例',exact=True).click()
   picker=page.get_by_label('选择模型',exact=True)
   assert await picker.locator('option').count()==6
   assert await picker.locator('option').nth(1).get_attribute('value')=='qwen3.7-flash'
   assert await page.get_by_text('＋ 添加模型…',exact=True).count()==0
   await picker.select_option('qwen3.8-max')
   await page.reload()
   await page.get_by_role('button',name='表达数据演示',exact=True).click()
   await page.get_by_role('button',name='报告示例',exact=True).click()
   assert await page.get_by_label('选择模型',exact=True).input_value()=='qwen3.8-max'
   await page.get_by_role('button',name='设置',exact=True).click()
   assert await page.get_by_label('模型名',exact=True).count()==0
   await page.get_by_role('button',name='关闭',exact=True).click()
   await page.get_by_role('button',name='成果').click()
   panel=page.locator('.artifacts-panel')
   assert await panel.get_by_text('report.html',exact=True).is_visible()
   assert await panel.get_by_text('report.pdf',exact=True).is_visible()
   assert await panel.get_by_text('pca.html',exact=True).count()==0
   assert await panel.get_by_text('analysis.json',exact=True).count()==0
   assert not await panel.get_by_text('pca.png',exact=True).is_visible()
   await page.screenshot(path=str(root/'artifacts/ui/model-catalog.png'))
   await panel.locator('summary').filter(has_text='PNG 图片').click()
   assert await panel.get_by_text('pca.png',exact=True).is_visible()
   assert not await panel.get_by_text('pca.svg',exact=True).is_visible()
   await page.get_by_label('消息',exact=True).fill('你好')
   async with page.expect_request('**/chats/c/turns') as request:
    await page.get_by_role('button',name='发送',exact=True).click()
   assert (await request.value).post_data_json['model']=='qwen3.8-max'
   await browser.close()
   print('Server catalog: six choices, no custom entry, persistence and outgoing model PASS; artifact groups PASS')
 finally: vite.terminate();vite.wait()
asyncio.run(main())
