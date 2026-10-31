from pathlib import Path
import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1] / "examples" / "expression-demo"
root.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261026)
genes = ["STAT1", "GBP5", "DUSP3", "KLF2", "IFIT3", "CXCL10", "ACTB", "GAPDH"] + [f"SIM_GENE_{i:03d}" for i in range(1, 113)]
samples = [f"S{i:02d}" for i in range(1, 13)]
values = rng.normal(6, .65, (len(genes), 12))
values[:6, 6:] += 1.8
values = np.round(np.maximum(values, .01), 4)
pd.DataFrame(values, index=pd.Index(genes, name="gene"), columns=samples).to_csv(root / "expression.csv")
pd.DataFrame({"sample_id": samples, "group": ["control"] * 6 + ["simulated_case"] * 6, "batch": ["A", "B"] * 6}).to_csv(root / "samples.csv", index=False)
pd.DataFrame({"sample_id": samples[:-1] + ["WRONG_SAMPLE"], "group": ["control"] * 6 + ["simulated_case"] * 6}).to_csv(root / "samples-mismatch.csv", index=False)
(root / "README.md").write_text('''# BioLens 合成表达数据演示

这些是人工生成的数据，仅用于软件演示和验证，不是真实患者数据，不能用于医学或疾病结论。

expression.csv：行是基因，列是12个样本，首列gene为基因ID。数值模拟已经处理的对数表达量；分析时 transform=none，不再归一化或取对数。
samples.csv：sample_id与矩阵列一一对应；group是演示分组（control/simulated_case），batch为演示批次。
前6个基因被人为加入组间偏移，用于验证PCA和表达图。其名称仅用于模拟，不代表这些基因的真实疾病效应。
samples-mismatch.csv：故意包含一个错误样本ID，用于失败案例，Agent应该停止分析并说明问题。

推荐提示词：请读取README后，用expression.csv和samples.csv按group分组，transform=none，展示PCA、样本相关性、热图，以及STAT1和GBP5的表达。生成报告，强调这是合成数据，不做疾病结论。
''', "utf-8")
print("Synthetic fixtures generated with seed 20261026.")
