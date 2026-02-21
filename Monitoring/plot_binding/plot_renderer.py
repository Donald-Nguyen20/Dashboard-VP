from __future__ import annotations
from typing import Optional, List, Tuple
import pandas as pd
from Monitoring.plot_binding.plot_spec import PlotSpec

from project1_main_tab.Plot_modules.line_chart import plot_line_chart
from project1_main_tab.Plot_modules.scatter_chart import plot_scatter_chart
from project1_main_tab.Plot_modules.bar_chart import plot_bar_chart

class _FakeCombo:
    def __init__(self, text: str):
        self._text = text
    def currentText(self) -> str:
        return self._text

def _parse_time_ranges(spec: PlotSpec) -> Optional[List[Tuple[pd.Timestamp, pd.Timestamp]]]:
    if not spec.time_ranges_iso:
        return None
    return [(pd.to_datetime(a), pd.to_datetime(b)) for a, b in spec.time_ranges_iso]

def _filter_single_range(df: pd.DataFrame, spec: PlotSpec) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if "Datetime" not in df.columns:
        return df
    if not spec.start_dt_iso or not spec.end_dt_iso:
        return df
    start_dt = pd.to_datetime(spec.start_dt_iso)
    end_dt = pd.to_datetime(spec.end_dt_iso)
    return df[(df["Datetime"] >= start_dt) & (df["Datetime"] <= end_dt)]

def render_plot(ax, canvas, df: pd.DataFrame, spec: PlotSpec):
    plot_like = type("PlotLike", (), {})()
    plot_like.ax = ax
    plot_like.canvas = canvas
    plot_like.df = df
    plot_like.selected_vars = list(spec.selected_vars)
    plot_like.scales = dict(spec.scales or {})
    plot_like.bar_color = spec.bar_color
    plot_like.hue_combo = _FakeCombo(spec.hue)

    chart = (spec.chart_type or "line").lower()

    time_ranges = _parse_time_ranges(spec)
    if time_ranges and chart in ("line", "bar"):
        if chart == "line":
            plot_line_chart(plot_like, df, time_ranges=time_ranges)
        else:
            plot_bar_chart(plot_like, df, time_ranges=time_ranges)
        return

    df_filtered = _filter_single_range(df, spec)

    if chart == "line":
        plot_line_chart(plot_like, df_filtered)
    elif chart == "scatter":
        plot_scatter_chart(plot_like, df_filtered)
    elif chart == "bar":
        plot_bar_chart(plot_like, df_filtered)
    else:
        ax.clear()
        ax.text(0.5, 0.5, f"Monitoring chưa hỗ trợ: {chart}", ha="center", va="center")
        canvas.draw_idle()