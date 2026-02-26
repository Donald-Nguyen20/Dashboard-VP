import pandas as pd
import plotly.graph_objs as go


def plotly_bar_max(
    df: pd.DataFrame,
    y_columns,
    title="Min/Max (stacked) by tag",
    time_ranges=None,
    min_color="#5245CA",
    max_color="#26A69A",
    label_size=16,
    show_min_label=True,    # ✅ bật hiển thị MIN
    show_max_label=True,    # ✅ hiển thị MAX
):
    """
    1 tag = 1 thanh duy nhất (stack):
      - phần dưới: MIN (màu min_color)
      - phần trên: (MAX - MIN) (màu max_color)

    Multi-range:
      - group theo từng time range (đứng cạnh nhau)
      - trong mỗi group vẫn stack (min + delta)
      - label MIN nằm trong phần xanh (inside)
      - label MAX nằm trên đỉnh thanh (outside)
      - label không bị chồng giữa các ranges nhờ offsetgroup
    """

    def _minmax(dfx: pd.DataFrame, cols):
        out = {}
        for col in cols:
            if col not in dfx.columns:
                continue
            s = pd.to_numeric(dfx[col], errors="coerce")
            mn = s.min(skipna=True)
            mx = s.max(skipna=True)
            if pd.notna(mn) and pd.notna(mx):
                out[col] = (float(mn), float(mx))
        return out

    # ================= MULTI-RANGE =================
    if time_ranges is not None and len(time_ranges) > 1 and "Datetime" in df.columns:
        range_data = []
        for start_dt, end_dt in time_ranges:
            dfr = df[(df["Datetime"] >= start_dt) & (df["Datetime"] <= end_dt)]
            if dfr.empty:
                continue
            mm = _minmax(dfr, y_columns)
            if mm:
                range_data.append(
                    (f"{start_dt.strftime('%Y-%m-%d')}→{end_dt.strftime('%Y-%m-%d')}", mm)
                )

        if not range_data:
            return plotly_bar_max(
                df, y_columns, title=title, time_ranges=None,
                min_color=min_color, max_color=max_color, label_size=label_size,
                show_min_label=show_min_label, show_max_label=show_max_label
            )

        tags = list(range_data[0][1].keys())
        if not tags:
            return plotly_bar_max(
                df, y_columns, title=title, time_ranges=None,
                min_color=min_color, max_color=max_color, label_size=label_size,
                show_min_label=show_min_label, show_max_label=show_max_label
            )

        fig = go.Figure()

        for idx, (label, mm) in enumerate(range_data):
            mins = [mm.get(t, (0.0, 0.0))[0] for t in tags]
            maxs = [mm.get(t, (0.0, 0.0))[1] for t in tags]
            deltas = [max(mx - mn, 0.0) for mn, mx in zip(mins, maxs)]

            # MIN (stack base) + label inside
            fig.add_trace(go.Bar(
                x=tags,
                y=mins,
                name=f"{label} | Min",
                marker_color=min_color,
                offsetgroup=str(idx),
                legendgroup=str(idx),
                text=[f"{v:.3g}" for v in mins] if show_min_label else None,
                textposition="inside" if show_min_label else None,
                textfont=dict(size=label_size, color="white") if show_min_label else None,
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Range: " + label + "<br>Min=%{y}<extra></extra>",
            ))

            # MAX (delta on top) + label outside at top = max real
            fig.add_trace(go.Bar(
                x=tags,
                y=deltas,
                name=f"{label} | Max",
                marker_color=max_color,
                offsetgroup=str(idx),
                legendgroup=str(idx),
                customdata=maxs,
                text=[f"{v:.3g}" for v in maxs] if show_max_label else None,
                textposition="outside" if show_max_label else None,
                textfont=dict(size=label_size, color="#111111") if show_max_label else None,
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Range: " + label + "<br>Max=%{customdata}<br>(Max-Min)=%{y}<extra></extra>",
            ))

        fig.update_layout(
            title=f"{title} - {len(range_data)} ranges",
            xaxis_title="Tag / Variable",
            yaxis_title="Value",
            template="plotly_white",
            barmode="stack",
            bargap=0.25,
            margin=dict(l=40, r=20, t=70, b=90),
            uniformtext=dict(minsize=max(12, label_size - 2), mode="show"),
        )
        fig.update_xaxes(tickangle=-35)
        return fig

    # ================= SINGLE RANGE =================
    mm = _minmax(df, y_columns)
    if not mm:
        fig = go.Figure()
        fig.update_layout(title="No numeric min/max values to plot", template="plotly_white")
        return fig

    tags = list(mm.keys())
    mins = [mm[t][0] for t in tags]
    maxs = [mm[t][1] for t in tags]
    deltas = [max(mx - mn, 0.0) for mn, mx in zip(mins, maxs)]

    order = sorted(range(len(tags)), key=lambda i: maxs[i], reverse=True)
    tags = [tags[i] for i in order]
    mins = [mins[i] for i in order]
    maxs = [maxs[i] for i in order]
    deltas = [deltas[i] for i in order]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=tags,
        y=mins,
        name="Min",
        marker_color=min_color,
        text=[f"{v:.3g}" for v in mins] if show_min_label else None,
        textposition="inside" if show_min_label else None,
        textfont=dict(size=label_size, color="white") if show_min_label else None,
        cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>Min=%{y}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        x=tags,
        y=deltas,
        name="Max",
        marker_color=max_color,
        customdata=maxs,
        text=[f"{v:.3g}" for v in maxs] if show_max_label else None,
        textposition="outside" if show_max_label else None,
        textfont=dict(size=label_size, color="#111111") if show_max_label else None,
        cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>Max=%{customdata}<br>(Max-Min)=%{y}<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Tag / Variable",
        yaxis_title="Value",
        template="plotly_white",
        barmode="stack",
        margin=dict(l=40, r=20, t=70, b=90),
        uniformtext=dict(minsize=max(12, label_size - 2), mode="show"),
    )
    fig.update_xaxes(tickangle=-35)
    return fig