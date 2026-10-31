# Pasilla 真实 RNA-seq 示例

这是 Bioconductor pasilla 数据包中的果蝇 Pasilla RNAi 敲低研究数据，不是合成数据。14,599个基因、7个样本：4个 untreated，3个 treated；同时存在 single-read 和 paired-end 测序类型。

数据包：https://bioconductor.org/packages/pasilla/ ，DOI 10.18129/B9.bioc.pasilla。
原始研究：Brooks et al., Genome Research 2011, PMID 20921232。
下载来源：https://github.com/bioc/pasilla/tree/RELEASE_3_21/inst/extdata 。原始两份文件保留，SHA256见 provenance.json。

expression.csv 由原始计数按样本总计数计算 CPM，再取 log2(CPM+1)，未过滤基因/样本。此变换仅用于探索，不等于 DESeq2/TMM 或方差稳定化；不能用本示例替代完整差异分析。处理脚本为 scripts/prepare_pasilla.py。
samples.csv 以 sample_id 对应矩阵列；group 为处理状态，library_type 为测序类型。

客户端操作：选择此目录，开启本地读取，选择可视化报告和 HTML + PDF。

推荐提示词：

> 阅读README.md。用expression.csv和samples.csv分析，group作为分组列，library_type作为技术因素列（batch_column），untreated作为参考组（reference_group）。输入已经是log2(CPM+1)，transform=none。生成HTML和PDF报告，重点区分处理状态与测序类型对PCA的描述性关联，展示解释率、样本分布、相关性、高变异基因、组均值差概览，并展示FBgn0000008和FBgn0000014的样本点。不需要外部检索，不把均值差当成显著差异或因果证据。

图表的比较方向为 treated − untreated，单位是输入尺度的均值差。没有p值/FDR，未对技术因素做调整。选定的两个基因仅用于展示，不预设其生物学意义。
