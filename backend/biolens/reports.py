"""Report orchestration: shared document, chart assets and format-specific exports."""
import json
import re
from collections import Counter
from pathlib import Path
import plotly.express as px
import plotly.io as pio
from .chart_theme import style
from .report_document import document
from .report_export import render_exports

async def export_report(output: Path, title: str, sections: list, papers: list, analysis: dict | None, formats: str, local_sources=None):
    output.mkdir(parents=True,exist_ok=True)
    local_sources=local_sources or []
    source={'title':title,'sections':sections,'papers':papers,'analysis':analysis,'format':formats,'local_sources':local_sources}
    (output/'report-source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2),'utf-8')
    figures=[(c,pio.read_json(output/f"{c['id']}.plotly.json")) for c in (analysis or {}).get('charts',[])]
    if papers:
        years=Counter(m.group(0) for p in papers if (m:=re.search(r'\b(?:19|20)\d{2}\b',p.get('year',''))))
        if years:
            years=dict(sorted(years.items()))
            fig=px.bar(x=list(years),y=list(years.values()),labels={'x':'发表年份','y':'本次检索文献数'})
            fig.update_traces(marker_color='#117C83',text=list(years.values()),textposition='outside')
            fig.update_yaxes(dtick=1)
            chart={'id':'literature_years','title':'检索文献的年份分布','caption':'仅统计本轮获取的文献，不代表整个领域的发表趋势；缺失年份的文献不计入。','height':450}
            fig=style(fig,450);fig.write_json(output/'literature_years.plotly.json');figures.append((chart,fig))
    (output/'report.html').write_text(document(title,sections,papers,analysis,figures,local_sources),'utf-8')
    generated=[output/'report.html'] if formats in {'html','both'} else []
    generated.extend(await render_exports(output,[c for c,_ in figures],formats))
    generated.extend([output/'report-source.json',*output.glob('*.csv')])
    return generated
