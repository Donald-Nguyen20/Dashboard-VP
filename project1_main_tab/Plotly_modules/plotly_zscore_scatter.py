"""Plotly Z-score Scatter - tương tự Plot tab (Modified Z-score)."""
import numpy as np
import pandas as pd
import plotly.graph_objs as go


def plotly_zscore_scatter(df: pd.DataFrame, x_col: str, y_col: str, threshold: float = 3.5, title: str = "Modified Z-score Scatter"):
    """Vẽ scatter với màu theo modified z-score (outlier = đỏ)."""
    x = df[x_col].dropna()
    y = df[y_col].dropna()
    mask = ~(x.isna() | y.isna())
    x = x[mask]
    y = y[mask]
    median_y = np.median(y)
    mad_y = np.median(np.abs(y - median_y))
    if mad_y == 0:
        return None
    modified_z = 0.6745 * (y - median_y) / mad_y
    is_outlier = np.abs(modified_z) > threshold
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x[~is_outlier],
        y=y[~is_outlier],
        mode="markers",
        name="Normal",
        marker=dict(size=8, color="#1976d2", opacity=0.7),
    ))
    fig.add_trace(go.Scatter(
        x=x[is_outlier],
        y=y[is_outlier],
        mode="markers",
        name="Outlier",
        marker=dict(size=10, color="red", symbol="x"),
    ))
    fig.update_layout(
        title=title,
        xaxis_title=x_col,
        yaxis_title=y_col,
        template="plotly_white",
        hovermode="closest",
    )
    return fig
