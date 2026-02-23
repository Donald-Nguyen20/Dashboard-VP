"""Plotly Boxplot - tương tự Plot tab."""
import pandas as pd
import plotly.graph_objs as go


def plotly_boxplot(df: pd.DataFrame, columns: list, title: str = "Boxplot"):
    """Vẽ boxplot cho các cột numeric."""
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
            boxpoints="outliers",
            marker_color="#1976d2",
            line_color="#0d47a1",
        ))
    fig.update_layout(
        title=title,
        template="plotly_white",
        yaxis_title="Value",
        showlegend=True,
    )
    return fig
