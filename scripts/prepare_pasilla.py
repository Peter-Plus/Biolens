"""Prepare the downloaded Bioconductor pasilla tables without gene/sample filtering."""
from pathlib import Path
import pandas as pd
import numpy as np
import json, hashlib
root=Path(__file__).resolve().parents[1];p=root/'examples/pasilla'
counts=pd.read_csv(p/'pasilla_gene_counts.tsv',sep='\t',index_col=0)
meta=pd.read_csv(p/'pasilla_sample_annotation.csv');meta['sample_id']=meta['file'].str.removesuffix('fb')
meta=meta.rename(columns={'condition':'group','type':'library_type'}).set_index('sample_id').loc[counts.columns].rename_axis('sample_id').reset_index()
meta[['sample_id','group','library_type']].to_csv(p/'samples.csv',index=False)
np.log2(counts.div(counts.sum(axis=0),axis=1)*1e6+1).to_csv(p/'expression.csv',float_format='%.8f')
info={'source':'https://github.com/bioc/pasilla/tree/RELEASE_3_21/inst/extdata','package_doi':'10.18129/B9.bioc.pasilla','publication_pmid':'20921232','transformation':'log2(count / sample_total * 1e6 + 1), all genes retained; exploratory library-size scaling, not DESeq2 normalization','genes':len(counts),'samples':len(counts.columns),'source_sha256':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['pasilla_gene_counts.tsv','pasilla_sample_annotation.csv']}}
(p/'provenance.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(info));print(meta[['sample_id','group','library_type']].to_string(index=False))
