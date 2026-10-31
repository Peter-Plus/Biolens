import json
from pathlib import Path
import nbformat

root=Path(__file__).resolve().parents[1]
nb=nbformat.read(root/'course/BioLens-course-report.ipynb',as_version=4)
nbformat.validate(nb)
code=[c for c in nb.cells if c.cell_type=='code']
assert all(c.execution_count is not None for c in code)
assert not any(o.output_type=='error' for c in code for o in c.outputs)
key=(root.parent/'key.txt').read_text('utf-8-sig').strip().encode()
targets=[]
for folder in ['backend','src','electron','scripts','docs','course','assets','examples']:
    for p in (root/folder).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            if key in p.read_bytes():
                targets.append(str(p.relative_to(root)))
assert not targets, 'Credential found in deliverable files: '+str(targets)
print(json.dumps({'notebook_code_cells':len(code),'notebook_errors':0,'credential_scan':'clean','evaluation_cases':len(list((root/'course/evaluation').glob('*.json')))},ensure_ascii=False))
