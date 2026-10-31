import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import httpx
from playwright.async_api import async_playwright
from biolens.config import DATA_DIR

root=Path(__file__).resolve().parents[1]
out=root/'artifacts'/'ui'
data=root/'.local'/'ui-live-data'
data.mkdir(exist_ok=True)
shutil.copy2(DATA_DIR/'settings.json',data/'settings.json')

async def main():
    env=dict(os.environ,BIOLENS_PORT='8765',BIOLENS_DATA=str(data))
    server=subprocess.Popen([sys.executable,'-m','biolens'],env=env,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL)
    vite=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1'],cwd=root,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL)
    try:
        async with httpx.AsyncClient() as client:
            for _ in range(80):
                try:
                    if (await client.get('http://127.0.0.1:8765/health')).is_success:break
                except httpx.RequestError:pass
                await asyncio.sleep(.5)
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            page=await browser.new_page(viewport={'width':1480,'height':960})
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            await page.goto('http://127.0.0.1:5173')
            await page.get_by_text('本地工作区',exact=True).wait_for()
            await page.get_by_role('button',name='创建项目',exact=True).click()
            await page.get_by_label('项目名称').fill('合成表达数据演示')
            await page.get_by_label('本地目录（可选）').fill(str(root/'examples'/'expression-demo'))
            await page.get_by_role('button',name='创建项目',exact=True).last.click()
            await page.get_by_role('switch',name='本地资料').click()
            await page.get_by_role('button', name='可视化报告', exact=True).click()
            await page.get_by_label('报告格式').select_option('both')
            await page.get_by_label('消息',exact=True).fill('请读取README.md，用expression.csv和samples.csv按group分组，transform=none，展示PCA、样本相关性、热图和STAT1/GBP5的表达，生成报告。说明这是合成数据，不作疾病结论。')
            await page.get_by_role('button',name='发送',exact=True).click()
            await page.locator('.artifact').filter(has_text='report.pdf').wait_for(timeout=180000)
            await page.get_by_role('button',name='发送',exact=True).wait_for(timeout=60000)
            await page.screenshot(path=str(out/'live-report.png'))
            await page.locator('.artifact').filter(has_text='report.html').get_by_role('button').first.click()
            await page.frame_locator('iframe').locator('.js-plotly-plot').first.wait_for(timeout=30000)
            await page.screenshot(path=str(out/'interactive-preview.png'))
            await page.get_by_role('button',name='返回文件列表').click()
            await page.locator('.artifact').filter(has_text='report.pdf').get_by_role('button').first.click()
            await page.screenshot(path=str(out/'pdf-preview.png'))
            assert not errors,errors
            # Inspect the executed course report in the same rendering engine.
            report=await browser.new_page(viewport={'width':1280,'height':900})
            await report.goto((root/'course/BioLens-course-report.html').as_uri())
            await report.screenshot(path=str(out/'course-report.png'))
            await browser.close()
        print(json.dumps({'live_ui_report':'passed','interactive_preview':'passed','page_errors':errors}))
    finally:
        server.terminate();vite.terminate()

asyncio.run(main())
