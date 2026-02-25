from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.graph_objects as go


def plotly_rolling_band(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    window: int = 50,
    band_sigma: float = 1.0,
    title: str | None = None,
) -> go.Figure:
    """
    Rolling mean + band (mean ± band_sigma * rolling_std).
    Dùng để nhìn hunting/rung hệ thống (volatility).
    """
    d = df[[x_col, y_col]].copy()
    d[x_col] = pd.to_datetime(d[x_col], errors="coerce")
    d[y_col] = pd.to_numeric(d[y_col], errors="coerce")
    d = d.dropna().sort_values(x_col)

    if len(d) < max(10, window):
        fig = go.Figure()
        fig.update_layout(title=f"Rolling band: {y_col} (not enough data)")
        return fig

    y = d[y_col]
    m = y.rolling(window=window, min_periods=max(5, window // 3)).mean()
    s = y.rolling(window=window, min_periods=max(5, window // 3)).std(ddof=0)
    upper = m + band_sigma * s
    lower = m - band_sigma * s

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=d[x_col], y=y, mode="lines",
        name=y_col,
        hovertemplate="%{x}<br>" + f"{y_col}: " + "%{y:.4f}<extra></extra>"
    ))

    # band fill (no fixed colors; Plotly defaults)
    fig.add_trace(go.Scatter(
        x=d[x_col], y=upper,
        mode="lines", name=f"Mean+{band_sigma}σ",
        line=dict(width=1),
        hovertemplate="%{x}<br>Upper: %{y:.4f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=d[x_col], y=lower,
        mode="lines", name=f"Mean-{band_sigma}σ",
        fill="tonexty",
        line=dict(width=1),
        hovertemplate="%{x}<br>Lower: %{y:.4f}<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=d[x_col], y=m, mode="lines",
        name=f"Rolling Mean({window})",
        hovertemplate="%{x}<br>Mean: %{y:.4f}<extra></extra>"
    ))

    fig.update_layout(
        title=title or f"Rolling Mean ± {band_sigma}σ: {y_col}",
        xaxis_title=x_col,
        yaxis_title=y_col,
        hovermode="x unified",
        legend=dict(orientation="h"),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig