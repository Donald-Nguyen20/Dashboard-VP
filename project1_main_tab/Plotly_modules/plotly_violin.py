"""Plotly Violin - tương tự Plot tab."""
import pandas as pd
import plotly.graph_objs as go


def plotly_violin(df: pd.DataFrame, columns: list, title: str = "Violin Plot"):
    """Vẽ violin plot cho các cột numeric."""
    fig = go.Figure()
    for col in columns:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        vals = df[col].dropna()
        if vals.empty:
            continue
        fig.add_trace(go.Violin(
            y=vals,
            name=col,
            box_visible=True,
            meanline_visible=True,
        ))
    fig.update_layout(
        title=title,
        template="plotly_white",
        yaxis_title="Value",
        showlegend=True,
    )
    return fig
