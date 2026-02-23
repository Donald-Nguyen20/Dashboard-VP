"""Plotly Histogram - mỗi feature 1 subplot riêng (giống Plot tab)."""
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots


def plotly_histogram(df: pd.DataFrame, columns: list, title: str = "Histogram", bins: int = 60):
    """Vẽ histogram - mỗi feature một subplot riêng."""
    selected = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if not selected:
        return None
    n = len(selected)
    ncols = 2 if n > 1 else 1
    nrows = int(np.ceil(n / ncols))
    subplot_titles = [f"{col}" for col in selected]
    fig = make_subplots(rows=nrows, cols=ncols, subplot_titles=subplot_titles,
                        horizontal_spacing=0.1, vertical_spacing=0.12)
    for idx, col in enumerate(selected):
        vals = df[col].dropna()
        if vals.empty:
            continue
        row = idx // ncols + 1
        col_pos = idx % ncols + 1
        fig.add_trace(
            go.Histogram(x=vals, nbinsx=bins, name=col,
                         hovertemplate=f"<b>{col}</b><br>%{{x}}<br>Count: %{{y}}<extra></extra>"),
            row=row, col=col_pos
        )
    fig.update_layout(
        title=title,
        template="plotly_white",
        showlegend=False,
    )
    fig.update_xaxes(title_text="Value")
    fig.update_yaxes(title_text="Frequency")
    return fig
