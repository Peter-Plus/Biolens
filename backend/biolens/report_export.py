"""Browser-backed export only; no analysis or narrative generation."""
import base64
import os
from urllib.parse import unquote
from playwright.async_api import async_playwright

async def render_exports(output, charts, formats):
    generated=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=os.getenv('BIOLENS_CHROMIUM') or None)
        try:
            page=await browser.new_page(viewport={'width':1280,'height':900})
            await page.goto((output/'report.html').as_uri(),wait_until='load')
            await page.evaluate('document.fonts.ready')
            if charts:
                await page.wait_for_function("Array.from(document.querySelectorAll('.js-plotly-plot')).every(x=>x._fullLayout)")
            for i,chart in enumerate(charts):
                for extension in ('svg','png'):
                    data_url=await page.evaluate("async ([index,format,height])=>Plotly.toImage(document.querySelectorAll('.js-plotly-plot')[index],{format,width:1100,height,scale:2})",[i,extension,chart.get('height',500)])
                    header,data=data_url.split(',',1)
                    destination=output/f'{chart["id"]}.{extension}'
                    destination.write_bytes(base64.b64decode(data) if ';base64' in header else unquote(data).encode('utf-8'))
                    generated.append(destination)
            if formats in {'pdf','both'}:
                # Plotly image export can mutate categorical axis rendering state.
                # Print from a fresh document, not the image-export session state.
                await page.reload(wait_until='load')
                await page.evaluate('document.fonts.ready')
                # Freeze each chart to vector SVG at print dimensions. This avoids
                # Chromium printing live Plotly categorical axes inconsistently.
                print_svgs=[]
                for i,chart in enumerate(charts):
                    data_url=await page.evaluate("async ([i,h])=>Plotly.toImage(document.querySelectorAll('.js-plotly-plot')[i],{format:'svg',width:688,height:h})",[i,min(chart.get('height',480)+80,660)])
                    header,data=data_url.split(',',1)
                    print_svgs.append(base64.b64decode(data).decode('utf-8') if ';base64' in header else unquote(data))
                await page.evaluate("svgs=>{document.querySelectorAll('.plot-frame').forEach((frame,i)=>{frame.innerHTML=svgs[i];const svg=frame.querySelector('svg');svg.style.width='100%';svg.style.height='auto';});}",print_svgs)
                await page.emulate_media(media='print')
                await page.evaluate('document.fonts.ready')
                path=output/'report.pdf'
                await page.pdf(path=str(path),format='A4',print_background=True,prefer_css_page_size=True,display_header_footer=True,
                               header_template='<span></span>',footer_template='<div style="font:9px Arial;color:#72838b;width:100%;padding:0 14mm;display:flex;justify-content:space-between"><span>BioLens · 研究分析报告</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
                generated.append(path)
        finally:
            await browser.close()
    return generated
