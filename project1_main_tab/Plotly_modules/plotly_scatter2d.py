"""Plotly Scatter 2D - giống Plot tab: hồi quy tuyến tính, màu theo residual, R²."""
import numpy as np
import pandas as pd
import plotly.graph_objs as go


def plotly_scatter2d(df: pd.DataFrame, x_col: str, y_col: str):
    """Scatter + regression line + màu theo |residual| + R² (giống Plot tab)."""
    if x_col not in df.columns or y_col not in df.columns:
        return None
    x_raw = df[x_col]
    y_raw = pd.to_numeric(df[y_col], errors="coerce")
    try:
        if np.issubdtype(x_raw.dtype, np.datetime64):
            x_numeric = pd.to_datetime(x_raw, errors="coerce").astype("int64") / 1e9
        else:
            x_numeric = pd.to_numeric(x_raw, errors="coerce")
    except Exception:
        x_numeric = pd.to_numeric(x_raw, errors="coerce")
    mask = ~(x_numeric.isna() | y_raw.isna())
    x_clean = x_numeric[mask].values
    y_clean = y_raw[mask].values
    datetime_series = df["Datetime"][mask] if "Datetime" in df.columns else None
    if len(x_clean) < 2:
        return None
    try:
        coeffs = np.polyfit(x_clean, y_clean, deg=1)
        poly_eq = np.poly1d(coeffs)
        y_pred = poly_eq(x_clean)
        residuals = y_clean - y_pred
        r_squared = 1 - (np.sum(residuals**2) / np.sum((y_clean - y_clean.mean())**2))
    except Exception:
        coeffs = [0, 0]
        poly_eq = np.poly1d(coeffs)
        r_squared = 0
        residuals = np.zeros_like(y_clean)
    a, b = coeffs
    eqn = f"y = {a:.4f}x + {b:.4f}  |  R² = {r_squared:.4f}"
    x_sorted = np.sort(x_clean)
    y_reg = poly_eq(x_sorted)
    hover_text = None
    if datetime_series is not None and len(datetime_series) == len(x_clean):
        dt_list = [f"{t:%Y-%m-%d %H:%M}" if pd.notna(t) else "N/A" for t in datetime_series]
        hover_text = [f"⏱ {dt}<br>X: {x:.2f}<br>Y: {y:.2f}" for dt, x, y in zip(dt_list, x_clean, y_clean)]
    fig = go.Figure()
    scatter_kw = dict(
        x=x_clean,
        y=y_clean,
        mode="markers",
        marker=dict(
            size=10,
            color=np.abs(residuals),
            colorscale="RdBu_r",
            colorbar=dict(title="|Residual|"),
            opacity=0.8,
        ),
        name=f"{y_col} vs {x_col}",
    )
    if hover_text:
        scatter_kw["text"] = hover_text
        scatter_kw["hovertemplate"] = "%{text}<extra></extra>"
    else:
        scatter_kw["hovertemplate"] = "X: %{x:.2f}<br>Y: %{y:.2f}<extra></extra>"
    fig.add_trace(go.Scatter(**scatter_kw))
    fig.add_trace(go.Scatter(
        x=x_sorted,
        y=y_reg,
        mode="lines",
        line=dict(color="red", dash="dash", width=2),
        name="Regression line",
    ))
    fig.update_layout(
        title=f"Scatter: {y_col} vs {x_col}<br><sub>{eqn}</sub>",
        xaxis_title=x_col,
        yaxis_title=y_col,
        template="plotly_white",
        showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    return fig
