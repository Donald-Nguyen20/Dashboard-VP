"""Plotly Boxen - tương tự Plot tab (letter-value plot)."""
import pandas as pd
import plotly.graph_objs as go


def plotly_boxen(df: pd.DataFrame, columns: list, title: str = "Boxen Plot"):
    """Vẽ boxen (letter-value) plot - Plotly không có boxen native, dùng Box với quartilemethod."""
    fig = go.Figure()
    for col in columns:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        vals = df[col].dropna()
        if vals.empty:
            continue
        fig.add_trace(go.Box(
            y=vals,
            name=col,
            boxpoints="all",
            quartilemethod="linear",
            marker_color="#7e57c2",
            line_color="#4a148c",
        ))
    fig.update_layout(
        title=title,
        template="plotly_white",
        yaxis_title="Value",
        showlegend=True,
    )
    return fig
