# project1_main_tab/Plotly_modules/plotly_line_chart.py
import pandas as pd
import plotly.graph_objs as go

def plotly_line_chart(df, x, y_columns, title="Multi-Line Chart"):
    fig = go.Figure()
    added = 0

    # parse X datetime nếu được (giống demo của anh)
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