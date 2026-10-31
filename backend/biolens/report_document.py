"""HTML composition only; shared structured results for screen and print."""
import html
from pathlib import Path
import plotly.io as pio

def esc(value):
    return html.escape(str(value))

def table(headers, rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join(f'<th>{esc(h)}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def document(title, sections, papers, analysis, figures, local_sources=None):
    nav = '<a href="#overview">研究概览</a>'
    charts = []
    for i, (chart, figure) in enumerate(figures):
        id = 'figure-'+str(i+1)
        nav += f'<a href="#{id}">{i+1}. {esc(chart["title"])}</a>'
        fragment = pio.to_html(figure, full_html=False, include_plotlyjs=(i == 0),
                               config={"displaylogo":False,"responsive":True,"scrollZoom":False,"toImageButtonOptions":{"format":"png","scale":2}}, div_id='plot-'+str(i+1))
        insight=f'<p class="chart-insight">{esc(chart["insight"])}</p>' if chart.get('insight') else ''
        charts.append(f'<section class="chart-section" id="{id}"><div class="figure-heading"><span class="figure-index">图 {i+1:02d}</span><h2>{esc(chart["title"])}</h2></div>{insight}<figure><div class="plot-frame">{fragment}</div><figcaption>{esc(chart["caption"])}</figcaption></figure></section>')
    overview=''
    if analysis:
        variance=analysis['pca_explained_variance']
        metrics=[(f"{analysis['samples']:,}",'样本'),(f"{analysis['genes']:,}",'输入基因'),(len(analysis['groups']),'分组'),(f'{sum(variance):.1%}','PC1 + PC2 解释率')]
        overview='<div class="metrics">'+''.join(f'<div class="metric"><strong>{esc(v)}</strong><span>{esc(k)}</span></div>' for v,k in metrics)+'</div>'
        overview+=f'<p class="lede">分组：{esc(" / ".join(f"{k} (n={v})" for k,v in analysis["groups"].items()))}。工具变换：{esc(analysis["transform"])}。</p>'
        overview+='<div class="note">'+esc(' '.join(analysis['limitations']))+'</div>'
    text=''.join(f'<section class="narrative"><h2>{esc(s.get("heading",""))}</h2><p>{esc(s.get("body","")).replace(chr(10),"<br>")}</p></section>' for s in sections)
    appendix='<section class="appendix" id="methods"><h2>方法、实验设计与数据来源</h2>'
    if analysis:
        appendix+='<p>输入数据不自动归一化。PCA仅移除零方差基因，不删除样本；相关性使用全部输入基因。所有图表与CSV来自同一份计算结果。</p>'
        associations=analysis.get('factor_associations',[])
        if associations:
            appendix+='<h3>主成分与分组因素的描述性关联</h3><p>表中比例为各类别均值之间的平方和 / 主成分总平方和，逐因素单独计算，非调整后解释率、非因果贡献、无显著性检验；小样本或多类别可能产生较高比例。</p>'
            appendix+=table(['因素','主成分','组间平方和比例'],[(a['factor'],a['component'],f"{a['variance_fraction']:.1%}") for a in associations])
        design=analysis.get('sample_design',[])
        if design:
            cols=list(design[0])[:8]
            appendix+='<h3>样本设计（最多展示30行）</h3>'+table(cols,[[row.get(c,'') for c in cols] for row in design[:30]])
        appendix+='<h3>输入文件校验</h3>'+''.join(f'<p>{esc(s["file"])}<br><span class="hash">SHA256 {esc(s["sha256"])}</span></p>' for s in analysis['sources'])
        if analysis.get('missing_requested_genes'):
            appendix+='<p>未找到的指定基因：'+esc(', '.join(analysis['missing_requested_genes']))+'</p>'
    if local_sources:
        appendix+='<h3>本地资料</h3><ul>'+''.join(f'<li>{esc(s["source"])}'+(f' · 第{esc(s["page"])}页' if s.get('page') else '')+'</li>' for s in local_sources)+'</ul>'
    appendix+='<h3>外部文献来源</h3>'
    if papers:
        appendix+='<ol class="refs">'+''.join(f'<li><a href="https://pubmed.ncbi.nlm.nih.gov/{esc(p["pmid"])}/">{esc(p["title"])}</a><br>{esc(p.get("year",""))} · PMID {esc(p["pmid"])} · 摘要证据</li>' for p in papers)+'</ol>'
    else:
        appendix+='<p class="empty">本轮未调用外部文献检索；数据来源与研究背景见正文和本地说明。</p>'
    appendix+='</section>'
    css=Path(__file__).with_name('report.css').read_text('utf-8-sig')
    return f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{css}</style></head><body><div class="report-shell"><nav class="report-nav" aria-label="报告目录"><strong>BioLens</strong>{nav}<a href="#methods">方法与来源</a></nav><main><header class="report-header" id="overview"><span class="brand">BioLens / 研究分析报告</span><h1>{esc(title)}</h1><p class="lede">从整体结构到样本证据，保留数据尺度与解释边界。</p></header>{overview}{text}{"".join(charts)}{appendix}<footer class="report-footer">BioLens 辅助分析 · 请结合实验设计复核。摘要不等同于全文证据；描述性差异不等同于统计显著。</footer></main></div></body></html>'

def analysis_page(analysis, figures):
    return document('表达数据探索',[],[],analysis,figures)
