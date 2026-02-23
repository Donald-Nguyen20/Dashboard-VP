"""Plotly Pairplot - tương tự Plot tab (scatter matrix)."""
import pandas as pd
import plotly.express as px


def plotly_pairplot(df: pd.DataFrame, columns: list, title: str = "Pairplot"):
    """Vẽ scatter matrix / pairplot cho các cột numeric."""
    selected = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if len(selected) < 2:
        return None
    plot_df = df[selected].dropna()
    if plot_df.empty:
        return None
    fig = px.scatter_matrix(plot_df, dimensions=selected[:6], title=title)  # giới hạn 6 cột
    fig.update_layout(template="plotly_white")
    return fig
