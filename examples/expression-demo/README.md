# BioLens 合成表达数据演示

这些是人工生成的数据，仅用于软件演示和验证，不是真实患者数据，不能用于医学或疾病结论。

expression.csv：行是基因，列是12个样本，首列gene为基因ID。数值模拟已经处理的对数表达量；分析时 transform=none，不再归一化或取对数。
samples.csv：sample_id与矩阵列一一对应；group是演示分组（control/simulated_case），batch为演示批次。
前6个基因被人为加入组间偏移，用于验证PCA和表达图。其名称仅用于模拟，不代表这些基因的真实疾病效应。
samples-mismatch.csv：故意包含一个错误样本ID，用于失败案例，Agent应该停止分析并说明问题。

推荐提示词：请读取README后，用expression.csv和samples.csv按group分组，transform=none，展示PCA、样本相关性、热图，以及STAT1和GBP5的表达。生成报告，强调这是合成数据，不做疾病结论。
