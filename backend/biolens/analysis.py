"""Orchestrate validated data, numerical summaries and reusable chart builders."""
import hashlib
import json
from pathlib import Path
from .expression_data import load_expression
from .expression_stats import summarize
from .expression_charts import build_charts
from .report_document import analysis_page


def analyze_expression(root, enabled, output: Path, matrix_file, samples_file, group_column, transform="none", genes=None, batch_column=None, reference_group=None):
    matrix, meta, matrix_path, samples_path = load_expression(root, matrix_file, samples_file, group_column, enabled, transform)
    output.mkdir(parents=True, exist_ok=True)
    stats = summarize(matrix, meta, group_column, batch_column, reference_group)
    figures = build_charts(matrix, meta, group_column, stats, genes, batch_column)
    for chart, figure in figures:
        figure.write_json(output / f"{chart['id']}.plotly.json")
    stats['scores'].to_csv(output/'pca_scores.csv',index=False,encoding='utf-8-sig')
    stats['correlation'].to_csv(output/'sample_correlation.csv',encoding='utf-8-sig')
    stats['qc'].to_csv(output/'sample_summary.csv',index=False,encoding='utf-8-sig')
    if stats['effects'] is not None:
        stats['effects'].to_csv(output/'group_effects.csv',index=False,encoding='utf-8-sig')
    summary = {'genes':int(matrix.shape[0]),'samples':int(matrix.shape[1]),'groups':meta[group_column].value_counts().to_dict(),
               'constant_genes':stats['constant_genes'],'pca_explained_variance':stats['variance'][:2].tolist(),
               'pca_variance_spectrum':stats['variance'].tolist(),'factor_associations':stats['associations'],
               'sample_summary':stats['qc'].to_dict('records'),'sample_design':meta.reset_index().to_dict('records'),
               'contrast':stats['contrast'],'top_effects':stats['effects'].head(12).to_dict('records') if stats['effects'] is not None else [],
               'missing_requested_genes':[g for g in genes or [] if g not in matrix.index],
               'transform':transform,'group_column':group_column,'batch_column':batch_column,'charts':[c for c,_ in figures],
               'limitations':['探索性分析，不构成疾病诊断或差异表达结论。','未自动校正技术因素，也未删除样本。','组均值差和主成分关联均为描述统计，不含p值/FDR或因果解释。'],
               'sources':[{'file':f,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for f,p in [(matrix_file,matrix_path),(samples_file,samples_path)]]}
    (output/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),'utf-8')
    (output/'analysis.html').write_text(analysis_page(summary, figures),'utf-8')
    return summary
