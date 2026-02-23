"""Plotly Histogram + Boxplot - tương tự Plot tab (subplot)."""
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots


def plotly_hist_box(df: pd.DataFrame, columns: list, title: str = "Histogram + Boxplot", bins: int = 60):
    """Vẽ Histogram và Boxplot cho mỗi biến (subplot)."""
    selected = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if not selected:
        return None
    n = len(selected)
    titles = [f"{c} (Hist)" for c in selected] + [f"{c} (Box)" for c in selected]
    fig = make_subplots(rows=n, cols=2, subplot_titles=titles[:n * 2],
                        column_widths=[0.7, 0.3], horizontal_spacing=0.06, vertical_spacing=0.1)
    for i, col in enumerate(selected):
        vals = df[col].dropna()
        if vals.empty:
            continue
        fig.add_trace(go.Histogram(x=vals, nbinsx=bins, showlegend=False), row=i + 1, col=1)
        fig.add_trace(go.Box(y=vals, showlegend=False), row=i + 1, col=2)
    fig.update_layout(title=title, template="plotly_white")
    return fig
