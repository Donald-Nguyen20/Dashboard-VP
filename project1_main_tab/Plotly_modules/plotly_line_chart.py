# project1_main_tab/Plotly_modules/plotly_line_chart.py
import pandas as pd
import plotly.graph_objs as go


def _get_range_colors(n):
    palette = ["#1976d2", "#d32f2f", "#388e3c", "#f57c00", "#7b1fa2", "#00796b", "#5d4037", "#455a64", "#c2185b", "#0097a7"]
    return [palette[i % len(palette)] for i in range(n)]


def plotly_line_chart(df, x, y_columns, title="Multi-Line Chart", time_ranges=None):
    fig = go.Figure()
    added = 0

    if time_ranges is not None and len(time_ranges) > 1 and x == "Datetime" and "Datetime" in df.columns:
        colors = _get_range_colors(len(time_ranges))
        for range_idx, (start_dt, end_dt) in enumerate(time_ranges):
            df_range = df[(df["Datetime"] >= start_dt) & (df["Datetime"] <= end_dt)]
            if df_range.empty:
                continue
            color = colors[range_idx]
            label_suffix = f" ({start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')})"
            for col in y_columns:
                if col not in df_range.columns:
                    continue
                y_vals = pd.to_numeric(df_range[col], errors="coerce")
                plot_df = pd.DataFrame({"x": df_range["Datetime"], "y": y_vals}).dropna()
                if plot_df.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=plot_df["x"], y=plot_df["y"], mode="lines",
                    name=col + label_suffix, line=dict(color=color, width=2),
                    hovertemplate=f"<b>{col}</b>: %{{y}}<extra></extra>",
                ))
                added += 1
        fig.update_layout(
            title=f"{title} - {len(time_ranges)} Ranges | {added} lines",
            xaxis_title=x,
            yaxis_title="Value",
            template="plotly_white",
            hovermode="x unified",
        )
        fig.update_xaxes(showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1)
        return fig

    # Single range
    x_raw = df[x]
    x_dt = pd.to_datetime(x_raw, errors="coerce")
    x_vals = x_dt if (x_dt.notna().mean() > 0.8) else x_raw

    for col in y_columns:
        if col not in df.columns:
            continue

        # ép numeric để tránh line "ảo" / không vẽ được
        y_vals = pd.to_numeric(df[col], errors="coerce")
        plot_df = pd.DataFrame({"x": x_vals, "y": y_vals}).dropna()
        if plot_df.empty:
            continue

        fig.add_trace(go.Scatter(
            x=plot_df["x"],
            y=plot_df["y"],
            mode="lines",
            name=col,
            hovertemplate=f"<b>{col}</b>: %{{y}}<extra></extra>"  # hiện từng dòng gọn
        ))
        added += 1

    # ==== “SCADA / scooter” style tooltip: show ALL values at same X ====
    fig.update_layout(
        title=f"{title} | {added} lines",
        xaxis_title=x,
        yaxis_title="Value",
        template="plotly_white",
        autosize=True,
        margin=dict(l=40, r=20, t=50, b=40),

        hovermode="x unified",     # <- quan trọng: bảng tooltip cho tất cả line
        hoverlabel=dict(
            align="left",
            namelength=-1
        ),
    )

    # spike line dọc theo cursor (rất giống DCS trend)
    fig.update_xaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikethickness=1
    )

    return fig