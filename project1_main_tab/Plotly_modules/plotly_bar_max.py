import pandas as pd
import plotly.graph_objs as go


def _get_range_colors(n):
    palette = ["#1976d2", "#d32f2f", "#388e3c", "#f57c00", "#7b1fa2", "#00796b", "#5d4037", "#455a64", "#c2185b", "#0097a7"]
    return [palette[i % len(palette)] for i in range(n)]


def plotly_bar_max(df: pd.DataFrame, y_columns, title="Max value by tag", time_ranges=None):
    if time_ranges is not None and len(time_ranges) > 1 and "Datetime" in df.columns:
        range_data = []
        for start_dt, end_dt in time_ranges:
            df_range = df[(df["Datetime"] >= start_dt) & (df["Datetime"] <= end_dt)]
            if df_range.empty:
                continue
            maxs = {}
            for col in y_columns:
                if col not in df_range.columns:
                    continue
                s = pd.to_numeric(df_range[col], errors="coerce")
                mx = s.max(skipna=True)
                if pd.notna(mx):
                    maxs[col] = float(mx)
            range_data.append({"maxs": maxs, "label": f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}"})
        if not range_data:
            return plotly_bar_max(df, y_columns, title=title)
        vars_used = list(range_data[0]["maxs"].keys())
        if not vars_used:
            return plotly_bar_max(df, y_columns, title=title)
        fig = go.Figure()
        colors = _get_range_colors(len(range_data))
        for r_idx, r_info in enumerate(range_data):
            y_vals = [r_info["maxs"].get(v, 0) for v in vars_used]
            fig.add_trace(go.Bar(
                name=r_info["label"],
                x=vars_used,
                y=y_vals,
                text=[f"{v:.2f}" for v in y_vals],
                textposition="outside",
                marker_color=colors[r_idx],
                hovertemplate="<b>%{x}</b><br>%{fullData.name}<br>max=%{y}<extra></extra>",
            ))
        fig.update_layout(
            title=f"Bar Comparison - {len(range_data)} Ranges",
            xaxis_title="Variable",
            yaxis_title="Max value",
            template="plotly_white",
            barmode="group",
            margin=dict(l=40, r=20, t=50, b=80),
        )
        fig.update_xaxes(tickangle=-35)
        return fig

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