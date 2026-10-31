import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
import httpx
from playwright.async_api import async_playwright

root = Path(__file__).resolve().parents[1]
out = root / "artifacts" / "ui"
out.mkdir(parents=True, exist_ok=True)

async def main():
    env = dict(os.environ, BIOLENS_PORT="8765", BIOLENS_DATA=str(root / ".local" / "ui-test-data"))
    server = subprocess.Popen([sys.executable, "-m", "biolens"], env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    vite = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1"], cwd=root, creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL)
    try:
        async with httpx.AsyncClient() as client:
            for _ in range(60):
                try:
                    if (await client.get("http://127.0.0.1:8765/health")).is_success:
                        break
                except httpx.RequestError:
                    pass
                await asyncio.sleep(.5)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page(viewport={"width": 1380, "height": 900}, device_scale_factor=1)
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto("http://127.0.0.1:5173")
            await page.get_by_text("本地工作区", exact=True).wait_for()
            await page.screenshot(path=str(out / "welcome.png"))
            await page.get_by_role("button", name="创建项目", exact=True).click()
            await page.get_by_label("项目名称").fill("表达数据研究")
            await page.get_by_label("本地目录（可选）").fill(str(root / "examples" / "expression-demo"))
            await page.get_by_role("button", name="创建项目", exact=True).last.click()
            await page.get_by_role("button", name="新聊天", exact=True).click()
            await page.get_by_role("switch", name="本地资料").click()
            await page.get_by_role("switch", name="外部检索").click()
            assert await page.get_by_role("switch", name="本地资料").get_attribute("aria-checked") == "true"
            await page.get_by_role("button", name="可视化报告", exact=True).click()
            await page.get_by_label("报告格式").select_option("both")
            await page.get_by_label("消息", exact=True).fill("请用项目中的表达矩阵和样本表，展示PCA、样本相关性和指定基因表达，生成HTML与PDF报告。")
            await page.screenshot(path=str(out / "report-mode.png"))
            await page.get_by_role("button", name="设置", exact=True).click()
            await page.screenshot(path=str(out / "settings.png"))
            await page.get_by_role("button", name="关闭", exact=True).click()
            assert not errors, errors
            # Render our SVG logo to PNG/ICO without image generation.
            icon = await browser.new_page(viewport={"width": 512, "height": 512})
            svg = (root / "assets" / "logo.svg").read_text("utf-8")
            await icon.set_content('<html><body style="margin:0;background:transparent">'+svg.replace('viewBox=', 'width="512" height="512" viewBox=')+'</body></html>')
            await icon.screenshot(path=str(root / "assets" / "icon.png"), omit_background=True)
            from PIL import Image
            Image.open(root / "assets" / "icon.png").save(root / "assets" / "icon.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
            await browser.close()
        print(json.dumps({"ui_errors": errors, "screenshots": ["welcome.png", "report-mode.png", "settings.png"], "project_and_switches": "passed"}))
    finally:
        server.terminate()
        vite.terminate()

asyncio.run(main())
