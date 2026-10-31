"""Numerical exploratory summaries, independent of rendering and model calls."""
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA


def summarize(matrix, meta, group_column, batch_column=None, reference_group=None):
    variable = matrix.var(axis=1) > 0
    if variable.sum() < 2:
        raise ValueError("至少需要两个有变化的基因；当前数据无法进行PCA。")
    if batch_column and (batch_column not in meta or meta[batch_column].isna().any()):
        raise ValueError("指定的技术因素列不存在或含缺失值。")
    working = matrix.loc[variable]
    pca = PCA(n_components=min(10, *working.shape), svd_solver="full")
    coords = pca.fit_transform(working.T)
    scores = pd.DataFrame(coords[:, :2], columns=["PC1", "PC2"], index=matrix.columns)
    scores["sample_id"] = scores.index
    scores[group_column] = meta[group_column]
    if batch_column:
        scores[batch_column] = meta[batch_column]
    corr = matrix.corr()
    if not np.isfinite(corr.to_numpy()).all():
        raise ValueError("某个样本的表达值没有变化，无法计算样本相关性。")
    top = working.var(axis=1).nlargest(min(30, len(working))).index
    heat = working.loc[top]
    heat = heat.sub(heat.mean(axis=1), axis=0).div(heat.std(axis=1), axis=0)
    # Cluster genes only; samples retain explicit group order for interpretability.
    from scipy.cluster.hierarchy import linkage, leaves_list
    heat = heat.iloc[leaves_list(linkage(heat.to_numpy(), method="average", metric="euclidean"))]
    order = sorted(matrix.columns, key=lambda sample: (str(meta.loc[sample, group_column]), str(sample)))
    qc = pd.DataFrame({"sample_id": matrix.columns, "median": matrix.median().values,
                       "zero_fraction": (matrix == 0).mean().values, "group": meta[group_column].values})
    associations = []
    for column in dict.fromkeys([group_column] + ([batch_column] if batch_column else [])):
        for pc in ["PC1", "PC2"]:
            values = scores[pc]
            total = float(((values-values.mean())**2).sum())
            between = sum(len(part)*(part.mean()-values.mean())**2 for _, part in values.groupby(meta[column]))
            associations.append({"factor": column, "component": pc, "variance_fraction": float(between/total) if total else 0.0})
    effects = None
    groups = list(meta[group_column].unique())
    if reference_group is not None:
        if len(groups) != 2 or reference_group not in groups:
            raise ValueError("组间效应概览需要恰好两组，且reference_group必须是已有组名。")
        target = next(g for g in groups if g != reference_group)
        ref = matrix.loc[:, meta[group_column] == reference_group]
        other = matrix.loc[:, meta[group_column] == target]
        effects = pd.DataFrame({"gene": matrix.index, "mean_expression": matrix.mean(axis=1),
                                "difference": other.mean(axis=1)-ref.mean(axis=1)})
        effects = effects.sort_values("difference", key=abs, ascending=False).reset_index(drop=True)
    return {"scores": scores, "variance": pca.explained_variance_ratio_, "correlation": corr,
            "heatmap": heat[order], "order": order, "qc": qc, "associations": associations,
            "effects": effects, "constant_genes": int((~variable).sum()),
            "contrast": {"reference": reference_group, "target": target} if effects is not None else None}
