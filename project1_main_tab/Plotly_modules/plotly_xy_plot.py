"""XY Plot — 1 biến X, nhiều biến Y, mỗi Y là 1 scatter trace riêng màu."""
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.colors as pc


def plotly_xy_plot(df: pd.DataFrame, x_col: str, y_cols: list[str]):
    """Vẽ nhiều biến Y lên cùng 1 trục X (scatter, không regression)."""
    if x_col not in df.columns:
        return None
    valid_y = [c for c in y_cols if c in df.columns]
    if not valid_y:
        return None

    x_raw = df[x_col]
    try:
        if np.issubdtype(x_raw.dtype, np.datetime64):
            x_vals = pd.to_datetime(x_raw, errors="coerce")
        else:
            x_vals = pd.to_numeric(x_raw, errors="coerce")
    except Exception:
        x_vals = pd.to_numeric(x_raw, errors="coerce")

    colors = pc.qualitative.Plotly
    fig = go.Figure()

    for i, y_col in enumerate(valid_y):
        y_vals = pd.to_numeric(df[y_col], errors="coerce")
        mask = x_vals.notna() & y_vals.notna()
        x_clean = x_vals[mask]
        y_clean = y_vals[mask]
        if len(x_clean) < 1:
            continue
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=x_clean,
            y=y_clean,
            mode="markers",
            marker=dict(size=7, color=color, opacity=0.75),
            name=y_col,
            hovertemplate=f"<b>{y_col}</b><br>{x_col}: %{{x}}<br>Y: %{{y:.3f}}<extra></extra>",
        ))

    if not fig.data:
        return None

    y_label = ", ".join(valid_y) if len(valid_y) <= 3 else f"{len(valid_y)} biến"
    fig.update_layout(
        title=f"XY Plot: {y_label} vs {x_col}",
        xaxis_title=x_col,
        yaxis_title="Giá trị",
        template="plotly_white",
        showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    return fig
