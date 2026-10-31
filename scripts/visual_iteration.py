"""Reproducible real-data report and visual inspection artifacts."""
import asyncio,json,sys
from pathlib import Path
import pymupdf
from playwright.async_api import async_playwright
from biolens.analysis import analyze_expression
from biolens.reports import export_report
root=Path(__file__).resolve().parents[1]
async def main():
 out=root/'artifacts/visual-iterations'/ (sys.argv[1] if len(sys.argv)>1 else 'round1')
 a=analyze_expression(str(root/'examples/pasilla'),True,out,'expression.csv','samples.csv','group',batch_column='library_type',reference_group='untreated',genes=['FBgn0000008','FBgn0000014'])
 assoc={(x['factor'],x['component']):x['variance_fraction'] for x in a['factor_associations']}
 sections=[{'heading':'研究问题与真实数据','body':'Pasilla 是果蝇 RNAi 敲低研究的公开 RNA-seq 数据。这里使用 Bioconductor pasilla 的基因计数：4个 untreated、3个 treated 样本，共14,599个基因。原始研究：Brooks 等，Genome Research 2011，PMID 20921232；数据包 DOI 10.18129/B9.bioc.pasilla。来源见 examples/pasilla/README.md。'},
 {'heading':'先分清处理效应与技术因素','body':f"PC1与PC2共同保留{sum(a['pca_explained_variance']):.1%}的表达变异。按单因素组间平方和计算，处理状态与PC1的描述性关联为{assoc[('group','PC1')]:.1%}，测序类型与PC1为{assoc[('library_type','PC1')]:.1%}。请结合颜色和点形状阅读PCA，不能把全部分离归因于处理。测序类型与PC2的描述性关联为{assoc[('library_type','PC2')]:.1%}，提醒我们第二个轴可能主要反映技术差异。两类因素的比例分别计算，不能相加，也不是调整后的效应。"},
 {'heading':'如何读这份报告','body':'从整体结构和解释率开始，再核对样本分布、相关性与高变异基因。组间效应图使用 treated − untreated 的表达均值差，候选排序只帮助回查数据。小样本且未校正测序类型，不据此报告显著差异基因。'},
 {'heading':'输入尺度与可复现性','body':'原始计数逐样本除以全部基因计数总和、乘以一百万，再取 log2(CPM+1)。保留全部基因和样本；这只是探索性的测序深度缩放，不是DESeq2/TMM或方差稳定化。工具 transform=none，不再次取对数。处理脚本和源文件SHA256随示例保存。'}]
 paths=await export_report(out,'Pasilla：区分处理效应与技术差异',sections,[],a,'both')
 doc=pymupdf.open(out/'report.pdf')
 page_info=[]
 for i,page in enumerate(doc):
  page.get_pixmap(matrix=pymupdf.Matrix(1,1)).save(out/f'page-{i+1}.png')
  page_info.append({'page':i+1,'chars':len(page.get_text()),'figures':page.get_text().count('图 0')})
 text='\n'.join(page.get_text() for page in doc)
 assert all(sample in doc[3].get_text() for sample in ['treated1','untreated4']), 'PDF sample axis clipped'
 assert 'FBgn0000008' in doc[8].get_text(), 'PDF gene axis clipped'
 async with async_playwright() as pw:
  browser=await pw.chromium.launch()
  page=await browser.new_page(viewport={'width':1440,'height':1000})
  await page.goto((out/'report.html').as_uri());await page.wait_for_function("document.querySelectorAll('.js-plotly-plot').length===8")
  await page.screenshot(path=str(out/'html-overview.png'))
  await page.locator('#figure-1').screenshot(path=str(out/'html-pca.png'))
  await page.locator('#figure-5').screenshot(path=str(out/'html-heatmap.png'))
  await page.set_viewport_size({'width':580,'height':900})
  await page.reload();await page.evaluate("scrollTo(0,0)");await page.screenshot(path=str(out/'html-narrow.png'))
  overflow=await page.evaluate('document.documentElement.scrollWidth > innerWidth')
  print(json.dumps({'pages':page_info,'charts':len(a['charts']),'narrow_overflow':overflow,'associations':a['factor_associations']},ensure_ascii=False),flush=True)
  await browser.close()
 (out/'review.json').write_text(json.dumps({'pages':page_info,'narrow_overflow':overflow},indent=2),'utf-8')
asyncio.run(main())
