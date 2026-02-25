from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.graph_objects as go


def plotly_spc_i_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    window: int = 50,
    sigma: float = 3.0,
    title: str | None = None,
) -> go.Figure:
    """
    SPC Control Chart (I-Chart) với rolling mean/std để theo dõi drift/violation.
    - window: số điểm dùng tính mean/std (nên 30~200 tùy sample rate)
    - sigma : 3-sigma (UCL/LCL)
    """
    d = df[[x_col, y_col]].copy()
    d[x_col] = pd.to_datetime(d[x_col], errors="coerce")
    d[y_col] = pd.to_numeric(d[y_col], errors="coerce")
    d = d.dropna().sort_values(x_col)

    if len(d) < max(10, window):
        fig = go.Figure()
        fig.update_layout(title=f"SPC I-Chart: {y_col} (not enough data)")
        return fig

    y = d[y_col]
    mean = y.rolling(window=window, min_periods=max(5, window // 3)).mean()
    std = y.rolling(window=window, min_periods=max(5, window // 3)).std(ddof=0)
    ucl = mean + sigma * std
    lcl = mean - sigma * std

    # violation points
    viol = (y > ucl) | (y < lcl)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=d[x_col], y=y, mode="lines",
        name=y_col,
        hovertemplate="%{x}<br>" + f"{y_col}: " + "%{y:.4f}<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=d[x_col], y=mean, mode="lines",
        name=f"Mean({window})",
        hovertemplate="%{x}<br>Mean: %{y:.4f}<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=d[x_col], y=ucl, mode="lines",
        name=f"UCL (+{sigma}σ)",
        hovertemplate="%{x}<br>UCL: %{y:.4f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=d[x_col], y=lcl, mode="lines",
        name=f"LCL (-{sigma}σ)",
        hovertemplate="%{x}<br>LCL: %{y:.4f}<extra></extra>"
    ))

    # highlight violations
    if viol.any():
        fig.add_trace(go.Scatter(
            x=d.loc[viol, x_col], y=d.loc[viol, y_col],
            mode="markers",
            name="Violation",
            marker=dict(size=8, symbol="circle"),
            hovertemplate="%{x}<br>Violation: %{y:.4f}<extra></extra>"
        ))

    fig.update_layout(
        title=title or f"SPC I-Chart: {y_col}",
        xaxis_title=x_col,
        yaxis_title=y_col,
        hovermode="x unified",
        legend=dict(orientation="h"),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig