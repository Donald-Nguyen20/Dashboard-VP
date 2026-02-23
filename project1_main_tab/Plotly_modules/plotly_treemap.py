"""Plotly Treemap - phân cấp theo giá trị."""
import pandas as pd
import plotly.graph_objs as go


def plotly_treemap(df: pd.DataFrame, columns: list, value_col: str = None, title: str = "Treemap"):
    """
    Treemap: mỗi biến = 1 nhánh, kích thước = giá trị (sum).
    value_col: cột dùng làm giá trị, mặc định = cột đầu tiên numeric.
    """
    selected = [c for c in columns if c in df.columns]
    if not selected:
        return None
    numeric_cols = [c for c in selected if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        return None
    vcol = value_col if value_col and value_col in df.columns else numeric_cols[0]
    labels = ["Total"]
    parents = [""]
    values = [df[vcol].sum()]
    for col in selected:
        if col not in df.columns:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            val = df[col].sum()
        else:
            val = df[col].count()
        labels.append(col)
        parents.append("Total")
        values.append(float(val))
    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        hovertemplate="<b>%{label}</b><br>Value: %{value}<extra></extra>",
    ))
    fig.update_layout(title=title, template="plotly_white")
    return fig
