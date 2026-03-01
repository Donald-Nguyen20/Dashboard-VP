from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.graph_objects as go


def plotly_100_stacked_bar(
    df: pd.DataFrame,
    value_cols: list[str],
    group_col: str | None = None,
    title: str = "100% Stacked Bar",
    decimals: int = 2,
    show_percent_text: bool = True,
    agg: str = "mean",
    time_ranges: list[tuple] | None = None,   # ✅ thêm
) -> go.Figure:

    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="No data")
        return fig

    # numeric check
    for c in value_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    fig = go.Figure()

    # ===============================
    # CASE 1 — Có multi range
    # ===============================
    if time_ranges and "Datetime" in df.columns:

        results = []

        for i, (start_dt, end_dt) in enumerate(time_ranges, 1):
            sub = df[(df["Datetime"] >= start_dt) & (df["Datetime"] <= end_dt)]
            if sub.empty:
                continue

            if agg == "sum":
                row = sub[value_cols].sum()
            elif agg == "median":
                row = sub[value_cols].median()
            else:
                row = sub[value_cols].mean()

            results.append((f"Range {i}", row))

        if not results:
            fig.update_layout(title="No data in selected ranges")
            return fig

        data = pd.DataFrame([r[1] for r in results],
                            index=[r[0] for r in results])

    # ===============================
    # CASE 2 — Không có range
    # ===============================
    else:
        if agg == "sum":
            row = df[value_cols].sum()
        elif agg == "median":
            row = df[value_cols].median()
        else:
            row = df[value_cols].mean()

        data = pd.DataFrame([row], index=["ALL"])

    # ===============================
    # Normalize thành %
    # ===============================
    totals = data.sum(axis=1).replace(0, np.nan)
    pct = (data.div(totals, axis=0) * 100.0).fillna(0.0)

    x = pct.index.tolist()

    for c in value_cols:
        y = pct[c].values
        text = [f"{v:.{decimals}f}%" if (show_percent_text and v > 0) else "" for v in y]

        fig.add_trace(go.Bar(
            name=c,
            x=x,
            y=y,
            text=text,
            textposition="inside",
            textfont=dict(size=20),
            hovertemplate=f"<b>%{{x}}</b><br>{c}: %{{y:.{decimals}f}}%<extra></extra>"
        ))

    fig.update_layout(
        title=title,
        barmode="stack",
        yaxis=dict(title="Percent (%)", range=[0, 100]),

        # ✅ legend bên phải
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            borderwidth=0
        ),

        margin=dict(l=40, r=150, t=60, b=40),  # tăng margin phải để đủ chỗ legend
    )

    return fig