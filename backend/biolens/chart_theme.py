"""Shared figure styling and stable categorical color mapping."""
PALETTE = ["#117C83", "#D4773B", "#7067A8", "#4088B8", "#B6517E", "#758D46"]
DIVERGING = [[0, "#225A91"], [.5, "#F8FAFA"], [1, "#BB5438"]]


def colors(groups):
    return {str(group): PALETTE[i % len(PALETTE)] for i, group in enumerate(sorted(set(groups)))}


def style(figure, height=480):
    figure.update_layout(template="plotly_white", height=height, autosize=True,
                         paper_bgcolor="white", plot_bgcolor="white",
                         font={"family": "Arial, Microsoft YaHei, sans-serif", "size": 12, "color": "#29434B"},
                         title={"text": ""}, margin={"l": 80, "r": 50, "t": 65, "b": 85},
                         legend={"orientation": "h", "y": 1.15, "x": 0, "title_text": ""},
                         hoverlabel={"bgcolor": "white"})
    figure.update_xaxes(showgrid=False, zeroline=False, automargin=True, linecolor="#D9E3E6")
    figure.update_yaxes(gridcolor="#EAF0F2", zeroline=False, automargin=True)
    return figure
