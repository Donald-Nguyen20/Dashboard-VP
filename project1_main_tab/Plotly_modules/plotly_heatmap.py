"""Plotly Heatmap Correlation - tương tự Plot tab."""
import pandas as pd
import plotly.graph_objs as go


def plotly_heatmap(df: pd.DataFrame, columns: list, method: str = "pearson", title: str = "Heatmap Correlation"):
    """Vẽ heatmap correlation cho các cột numeric."""
    selected = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if len(selected) < 2:
        return None
    corr_df = df[selected].corr(method=method)
    fig = go.Figure(data=go.Heatmap(
        z=corr_df.values,
        x=corr_df.columns.tolist(),
        y=corr_df.index.tolist(),
        colorscale="RdBu_r",
        zmid=0,
        text=corr_df.round(2).values,
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverongaps=False,
    ))
    fig.update_layout(
        title=title,
        template="plotly_white",
        xaxis=dict(tickangle=45),
    )
    return fig
