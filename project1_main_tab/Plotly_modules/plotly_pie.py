"""Plotly Pie - tỷ lệ phần trăm, cấu trúc."""
import pandas as pd
import plotly.graph_objs as go


def plotly_pie(df: pd.DataFrame, columns: list, title: str = "Pie Chart", aggregator: str = "sum"):
    """
    Pie: giá trị trung bình hoặc tổng theo từng biến.
    aggregator: 'sum' | 'mean' | 'count'
    """
    selected = [c for c in columns if c in df.columns]
    if not selected:
        return None
    labels = []
    values = []
    for col in selected:
        if pd.api.types.is_numeric_dtype(df[col]):
            if aggregator == "sum":
                val = df[col].sum()
            elif aggregator == "mean":
                val = df[col].mean()
            else:
                val = df[col].count()
        else:
            val = df[col].count()
        labels.append(col)
        values.append(float(val))
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.3,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Value: %{value}<br>%{percent}<extra></extra>",
    )])
    fig.update_layout(title=title, template="plotly_white", showlegend=True)
    return fig
