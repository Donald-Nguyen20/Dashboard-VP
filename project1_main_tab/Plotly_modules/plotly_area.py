"""Plotly Area - xu hướng tích lũy theo thời gian (stacked area)."""
import pandas as pd
import plotly.graph_objs as go


def plotly_area(df: pd.DataFrame, x_col: str, y_columns: list, stacked: bool = True, title: str = "Area Chart"):
    """Area chart theo thời gian - giống Line nhưng fill."""
    if "Datetime" not in df.columns and x_col not in df.columns:
        return None
    x_raw = df[x_col]
    try:
        is_dt = pd.api.types.is_datetime64_any_dtype(x_raw) or (x_raw.dtype == object and pd.to_datetime(x_raw, errors="coerce").notna().mean() > 0.5)
    except Exception:
        is_dt = False
    x_vals = pd.to_datetime(x_raw, errors="coerce") if is_dt else x_raw
    fig = go.Figure()
    for col in y_columns:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        y_vals = pd.to_numeric(df[col], errors="coerce")
        plot_df = pd.DataFrame({"x": x_vals, "y": y_vals}).dropna()
        if plot_df.empty:
            continue
        fig.add_trace(go.Scatter(
            x=plot_df["x"],
            y=plot_df["y"],
            mode="lines",
            name=col,
            fill="tonexty" if stacked and len(fig.data) > 0 else "tozeroy",
            line=dict(width=0.5),
            hovertemplate=f"<b>{col}</b>: %{{y}}<extra></extra>",
        ))
    fig.update_layout(
        title=title,
        xaxis_title=x_col,
        yaxis_title="Value",
        template="plotly_white",
        hovermode="x unified",
    )
    return fig
