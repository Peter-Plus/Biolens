import asyncio
import os
import subprocess
import sys
from pathlib import Path
import httpx
from playwright.async_api import async_playwright
root=Path(__file__).resolve().parents[1]

async def main():
    server=subprocess.Popen([sys.executable,'-m','biolens'],env=dict(os.environ,BIOLENS_PORT='8765',BIOLENS_DATA=str(root/'.local/ui-live-data')),creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL)
    vite=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1'],cwd=root,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL)
    try:
        async with httpx.AsyncClient() as client:
            for _ in range(60):
                try:
                    if (await client.get('http://127.0.0.1:8765/health')).is_success:break
                except httpx.RequestError:pass
                await asyncio.sleep(.5)
        async with async_playwright() as pw:
            browser=await pw.chromium.launch()
            page=await browser.new_page(viewport={'width':1480,'height':960})
            await page.goto('http://127.0.0.1:5173')
            await page.get_by_role('button',name='合成表达数据演示',exact=True).first.click()
            await page.locator('.chat-list button').first.click()
            await page.locator('.topbar .subtle-button').click()
            await page.locator('.artifact').filter(has_text='report.pdf').get_by_role('button').first.click()
            image=page.frame_locator('iframe').locator('img').first
            await image.wait_for()
            await image.evaluate('(img)=>img.decode()')
            await page.screenshot(path=str(root/'artifacts/ui/pdf-preview.png'))
            assert await image.evaluate('(img)=>img.naturalWidth') > 500
            await browser.close()
        print('PDF preview page rendered: PASS')
    finally:
        server.terminate();vite.terminate()
asyncio.run(main())
