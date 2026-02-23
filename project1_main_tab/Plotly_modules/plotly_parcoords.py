"""Plotly Parallel Coordinates - tọa độ song song, so sánh nhiều biến."""
import pandas as pd
import plotly.express as px


def plotly_parcoords(df: pd.DataFrame, columns: list, title: str = "Parallel Coordinates"):
    """Parallel Coordinates: mỗi trục = 1 biến, mỗi line = 1 dòng dữ liệu."""
    selected = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if len(selected) < 2:
        return None
    plot_df = df[selected].dropna()
    if plot_df.empty:
        return None
    if len(plot_df) > 3000:
        plot_df = plot_df.sample(3000, random_state=42)
    fig = px.parallel_coordinates(plot_df, dimensions=selected, title=title)
    fig.update_layout(template="plotly_white")
    return fig
