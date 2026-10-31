import numpy as np
import pandas as pd
import pytest
from biolens.expression_stats import summarize
from biolens.report_document import document

def test_effect_direction_and_descriptive_factor_association():
    matrix=pd.DataFrame([[1.,2,7,8],[2,4,3,8],[0,1,4,5]],index=['a','b','c'],columns=['s1','s2','s3','s4'])
    meta=pd.DataFrame({'group':['control','control','treated','treated'],'batch':['a','b','a','b']},index=matrix.columns)
    result=summarize(matrix,meta,'group','batch','control')
    effects=result['effects'].set_index('gene').difference
    np.testing.assert_allclose(effects.loc[matrix.index],matrix[['s3','s4']].mean(axis=1)-matrix[['s1','s2']].mean(axis=1))
    for a in result['associations']:
        assert 0<=a['variance_fraction']<=1+1e-12
    assert len(result['heatmap'].columns)==4
    with pytest.raises(ValueError): summarize(matrix,meta,'group','missing')
    with pytest.raises(ValueError): summarize(matrix,meta,'group',reference_group='missing')

def test_report_text_is_escaped_and_offline():
    value=document('<script>bad</script>',[{'heading':'<img src=x>','body':'<script>alert(1)</script>'}],[],None,[])
    assert '<script>bad' not in value and '&lt;script&gt;bad' in value
    assert '<img src=x>' not in value
    assert 'viewport' in value and '报告目录' in value
