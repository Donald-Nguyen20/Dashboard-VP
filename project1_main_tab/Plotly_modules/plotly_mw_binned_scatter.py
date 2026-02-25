from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.graph_objects as go


def plotly_mw_binned_scatter(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    mw_col: str = "NET MW",
    bin_size: float = 50.0,
    max_bins: int = 8,
    title: str | None = None,
) -> go.Figure:
    """
    Scatter X-Y nhưng chia theo MW bins (rất đúng với nhà máy điện).
    - bin_size: MW mỗi bin (vd 50MW)
    - max_bins : giới hạn số bin để tránh quá nhiều trace
    """
    cols = [x_col, y_col, mw_col]
    d = df[cols].copy()
    d[x_col] = pd.to_datetime(d[x_col], errors="coerce")
    d[y_col] = pd.to_numeric(d[y_col], errors="coerce")
    d[mw_col] = pd.to_numeric(d[mw_col], errors="coerce")
    d = d.dropna().sort_values(x_col)

    fig = go.Figure()
    if len(d) < 10:
        fig.update_layout(title=f"MW-binned Scatter: {x_col} vs {y_col} (not enough data)")
        return fig

    mw_min = float(np.nanmin(d[mw_col]))
    mw_max = float(np.nanmax(d[mw_col]))
    if not np.isfinite(mw_min) or not np.isfinite(mw_max) or mw_max <= mw_min:
        fig.update_layout(title=f"MW-binned Scatter: invalid MW range")
        return fig

    # build bin edges
    start = np.floor(mw_min / bin_size) * bin_size
    end = np.ceil(mw_max / bin_size) * bin_size
    edges = np.arange(start, end + bin_size, bin_size)
    if len(edges) < 2:
        edges = np.array([mw_min, mw_max])

    # bin label
    d["__mw_bin__"] = pd.cut(d[mw_col], bins=edges, include_lowest=True)

    # pick top bins by count (avoid 30 bins)
    bin_counts = d["__mw_bin__"].value_counts().sort_values(ascending=False)
    top_bins = bin_counts.head(max_bins).index.tolist()

    for b in top_bins:
        dd = d[d["__mw_bin__"] == b]
        if len(dd) < 5:
            continue
        fig.add_trace(go.Scatter(
            x=dd[x_col],
            y=dd[y_col],
            mode="markers",
            name=str(b),
            marker=dict(size=6),
            hovertemplate="%{x}<br>" + f"{y_col}: " + "%{y:.4f}<br>" + f"{mw_col}: " + "%{customdata:.2f}<extra></extra>",
            customdata=dd[mw_col].to_numpy(),
        ))

    fig.update_layout(
        title=title or f"MW-binned Scatter: {y_col} vs Time (colored by MW bins)",
        xaxis_title=x_col,
        yaxis_title=y_col,
        legend=dict(orientation="h"),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig