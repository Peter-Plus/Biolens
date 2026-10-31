"""Validated, scoped expression input. No implicit normalization."""
from pathlib import Path
import numpy as np
import pandas as pd
from .local import resolve_file

def load_expression(root, matrix_file, samples_file, group_column, enabled, transform="none"):
    matrix_path = resolve_file(root, matrix_file, enabled)
    samples_path = resolve_file(root, samples_file, enabled)
    for path in (matrix_path, samples_path):
        if path.suffix.lower() not in {".csv", ".tsv"}:
            raise ValueError("表达矩阵和样本表必须是 CSV 或 TSV。")
        if path.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("首版支持不超过100 MB的表格。")
    # Check original header before pandas can silently rename duplicate columns.
    import csv
    with matrix_path.open(encoding="utf-8-sig") as f:
        header = next(csv.reader(f, delimiter="\t" if matrix_path.suffix.lower() == ".tsv" else ","))
    if len(set(header[1:])) != len(header[1:]):
        raise ValueError("表达矩阵存在重复样本列。")
    matrix = pd.read_csv(matrix_path, sep="\t" if matrix_path.suffix.lower() == ".tsv" else ",", index_col=0)
    meta = pd.read_csv(samples_path, sep="\t" if samples_path.suffix.lower() == ".tsv" else ",", dtype=str)
    if "sample_id" not in meta or group_column not in meta:
        raise ValueError(f"样本表必须包含 sample_id 和 {group_column} 列，请确认分组列。")
    if matrix.index.duplicated().any() or matrix.index.isna().any() or meta.sample_id.duplicated().any():
        raise ValueError("基因名或样本ID重复/缺失，请先修正。")
    matrix.index = matrix.index.map(str)
    if matrix.shape[0] < 2 or matrix.shape[1] < 3:
        raise ValueError("探索分析至少需要2个基因、3个样本。")
    if matrix.shape[1] > 500 or matrix.shape[0] > 100000:
        raise ValueError("首版最多支持500个样本和100000个基因。")
    if set(matrix.columns) != set(meta.sample_id):
        raise ValueError("表达矩阵样本列与样本表 sample_id 不完全一致；不会自动删除或补齐样本。")
    if meta[group_column].isna().any():
        raise ValueError("样本分组包含缺失值。")
    matrix = matrix.apply(pd.to_numeric, errors="raise")
    if not np.isfinite(matrix.to_numpy()).all():
        raise ValueError("表达矩阵包含缺失值或无穷值，请明确处理方式。")
    meta = meta.set_index("sample_id").loc[matrix.columns].rename_axis("sample_id")
    if transform == "log1p":
        if (matrix < 0).any().any():
            raise ValueError("负值不能使用本工具的 log1p 变换。")
        matrix = np.log1p(matrix)
    elif transform != "none":
        raise ValueError("transform 仅支持 none 或 log1p。")
    return matrix, meta, matrix_path, samples_path

