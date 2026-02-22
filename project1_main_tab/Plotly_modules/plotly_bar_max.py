import pandas as pd
import plotly.graph_objs as go

def plotly_bar_max(df: pd.DataFrame, y_columns, title="Max value by tag"):

    rows = []

    for col in y_columns:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        mx = s.max(skipna=True)
        if pd.isna(mx):
            continue
        rows.append((col, float(mx)))

    if not rows:
        fig = go.Figure()
        fig.update_layout(
            title="No numeric max values to plot",
            template="plotly_white"
        )
        return fig

    rows.sort(key=lambda x: x[1], reverse=True)

    x = [r[0] for r in rows]
    y = [r[1] for r in rows]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=x,
        y=y,
        text=[f"{v:.3g}" for v in y],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>max=%{y}<extra></extra>"
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Tag / Variable",
        yaxis_title="Max value",
        template="plotly_white",
        margin=dict(l=40, r=20, t=50, b=60),
    )

    fig.update_xaxes(tickangle=-35)

    return fig