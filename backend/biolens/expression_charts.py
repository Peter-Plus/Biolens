"""Figures from computed summaries. No statistical tests are inferred here."""
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from .chart_theme import style, colors, DIVERGING


def build_charts(matrix, meta, group_column, stats, genes=None, batch_column=None):
    palette = colors(meta[group_column])
    charts = []
    def add(id, title, caption, fig, height=480, insight=""):
        charts.append(({"id": id, "title": title, "caption": caption, "height": height, "insight": insight}, style(fig, height)))
    scores, variance = stats["scores"], stats["variance"]
    fig = px.scatter(scores, x="PC1", y="PC2", color=group_column, symbol=batch_column,
                     color_discrete_map=palette, hover_name="sample_id", text="sample_id" if len(scores)<=20 else None,
                     labels={"PC1": f"PC1 · {variance[0]:.1%}", "PC2": f"PC2 · {variance[1]:.1%}"})
    fig.update_traces(marker={"size": 12, "line": {"width": 1.2, "color": "white"}}, textposition="top center")
    for trace in fig.data:
        trace.textposition=[['top left','bottom right','top right','bottom left'][i%4] for i in range(len(trace.x))]
        trace.cliponaxis=False
    fig.update_yaxes(scaleanchor='x',scaleratio=1)
    add("pca", "整体表达结构", "基因中心化PCA，未进行方差缩放。颜色表示生物分组" + (f"，形状表示{batch_column}" if batch_column else "") + "。坐标等比例显示，分离不是显著性或因果证据。", fig,
        insight=f"前两个主成分保留 {sum(variance[:2]):.1%} 的总体表达变异；仍有 {1-sum(variance[:2]):.1%} 未在这张二维图中呈现。")
    pcs = [f"PC{i+1}" for i in range(len(variance))]
    fig = go.Figure(go.Bar(x=pcs, y=variance*100, marker_color="#117C83", name="单个主成分"))
    fig.add_trace(go.Scatter(x=pcs, y=np.cumsum(variance)*100, mode="lines+markers", marker_color="#D4773B", name="累计解释率"))
    fig.update_yaxes(title="解释方差 (%)", range=[0,105])
    add("variance", "主成分保留了多少信息", "最多展示前10个主成分；累计解释率用于判断二维投影丢失的信息，不是模型预测准确率。", fig, 400,
        insight=f"PC1 解释 {variance[0]:.1%}，PC2 解释 {variance[1]:.1%}。优先核对哪些实验因素与这些轴相关。")
    order = stats["order"]
    fig = go.Figure()
    for group in sorted(palette):
        names=[s for s in order if meta.loc[s,group_column]==group]
        values=matrix[names]
        quantiles=values.quantile([0,.25,.5,.75,1])
        # Precomputed quantiles avoid shipping every expression value to the browser.
        fig.add_trace(go.Box(x=names,q1=quantiles.loc[.25],median=quantiles.loc[.5],q3=quantiles.loc[.75],
                             lowerfence=quantiles.loc[0],upperfence=quantiles.loc[1],name=group,marker_color=palette[group],boxpoints=False))
    fig.update_yaxes(title="输入表达值（分析尺度）")
    fig.update_xaxes(categoryorder="array", categoryarray=order, tickangle=-30)
    add("distribution", "逐样本表达分布", "箱体为25%–75%分位数，中线为中位数，须为最小值/最大值（不是1.5×IQR）。用于检查整体分布，不能单独判断样本质量。", fig,
        insight=f"样本中位数范围 {matrix.median().min():.3f}–{matrix.median().max():.3f}（输入尺度）；本工具未进行额外归一化。")
    corr=stats["correlation"].loc[order,order]
    lower=max(-1, float(np.floor(corr.to_numpy().min()*100)/100))
    fig=px.imshow(corr,zmin=lower,zmax=1,color_continuous_scale="Teal",aspect="auto",text_auto=".3f" if len(order)<=15 else False)
    fig.update_coloraxes(colorbar_title="Pearson r")
    fig.update_xaxes(tickangle=-40)
    offdiag=corr.to_numpy()[np.triu_indices(len(corr),1)]
    add("correlation", "样本之间有多相似", f"全部输入基因的Pearson相关系数。色标范围{lower:.2f}–1.00，以突出样本间细微差异；相关系数仍在悬停中完整展示。样本按组排序。", fig, 540,
        insight=f"不同样本之间 r 的范围为 {offdiag.min():.4f}–{offdiag.max():.4f}。高相关性仍可能同时伴随少数基因的重要变化。")
    heat=stats["heatmap"]
    fig=px.imshow(heat,zmin=-2.5,zmax=2.5,color_continuous_scale=DIVERGING,aspect="auto")
    fig.update_coloraxes(colorbar_title="行 z-score")
    fig.update_xaxes(tickangle=-35)
    fig.update_yaxes(tickfont_size=10)
    add("heatmap", "高变异基因的表达模式", "最多30个高方差基因；逐行z-score。基因按平均连接/欧氏距离聚类，样本按组排序。超过±2.5的颜色饱和，不代表差异显著。", fig, 680)
    effects=stats["effects"]
    if effects is not None:
        contrast=stats["contrast"]
        # Full values remain in CSV; deterministic display cap prevents huge HTML.
        sampled=effects.iloc[np.linspace(0,len(effects)-1,min(15000,len(effects)),dtype=int)]
        fig=go.Figure(go.Scatter(x=sampled.mean_expression,y=sampled.difference,customdata=sampled.gene,
                                mode="markers",marker={"size":4,"color":"#91A6B2","opacity":.4},name="基因",
                                hovertemplate="%{customdata}<br>均值 %{x:.3f}<br>均值差 %{y:.3f}<extra></extra>"))
        top=effects.head(10)
        fig.add_trace(go.Scatter(x=top.mean_expression,y=top.difference,customdata=top.gene,mode="markers",marker={"size":8,"color":"#D4773B"},name="绝对均值差前10",
                                hovertemplate="%{customdata}<br>均值 %{x:.3f}<br>均值差 %{y:.3f}<extra></extra>"))
        fig.add_hline(y=0,line_dash="dot",line_color="#78909A")
        fig.update_xaxes(title="所有样本的平均表达值")
        fig.update_yaxes(title=f"均值差：{contrast['target']} − {contrast['reference']}")
        add("effects", "组间效应与表达水平", "纵轴为分析尺度上的组均值差，不是未经说明的log2 fold change；未估计p值或FDR，未校正技术因素。最多等距展示15,000个排序后的基因，完整结果见CSV。",fig)
        top=effects.head(12).sort_values('difference')
        fig=go.Figure(go.Bar(x=top.difference,y=top.gene,orientation="h",marker_color=["#D4773B" if v>0 else "#117C83" for v in top.difference]))
        fig.update_xaxes(title="组均值差（分析尺度）")
        add("effect_ranking", "值得回查的效应候选", "按绝对组均值差选取前12个基因，仅供回查原始数据。极端值、低表达与技术差异均可能驱动排序；不是显著差异基因名单。", fig)
    selected=[g for g in dict.fromkeys(genes or []) if g in matrix.index][:12]
    if selected:
        long=matrix.loc[selected].T.rename_axis('sample_id').reset_index().melt(id_vars='sample_id',var_name='gene',value_name='expression')
        long=long.merge(meta[[group_column]],left_on='sample_id',right_index=True)
        fig=px.box(long,x='gene',y='expression',color=group_column,points='all',hover_data=['sample_id'],color_discrete_map=palette)
        fig.update_traces(jitter=.25,marker_size=6)
        add("genes", "指定基因的样本级证据", "保留每一个样本点，展示组内离散程度；未进行显著性检验。",fig)
    return charts
