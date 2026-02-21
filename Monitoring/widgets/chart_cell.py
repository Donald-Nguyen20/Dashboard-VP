"""
Widget ô đồ thị - render chart từ Plot modules với config + df.
"""
from __future__ import annotations
from typing import Optional, Any
import pandas as pd
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class _PlotAdapter:
    """Adapter giống PlotTab để gọi plot_* từ Plot_modules."""
    def __init__(self, figure: Figure, chart_config: dict):
        self.figure = figure
        self.ax = figure.add_subplot(111)
        self.canvas = None  # gán sau
        self.df = pd.DataFrame()
        self.selected_vars = chart_config.get("vars", [])
        self.scales = chart_config.get("scales", {})


def _render_chart(
    adapter: _PlotAdapter,
    df: pd.DataFrame,
    chart_type: str,
) -> bool:
    """Render chart lên adapter.axes. Trả về True nếu thành công."""
    if df is None or df.empty:
        return False
    adapter.df = df

    # Filter theo time range nếu có
    if "start" in adapter.selected_vars or "Datetime" in df.columns:
        df_work = df.copy()
    else:
        df_work = df

    if "Datetime" in df_work.columns:
        df_work["Datetime"] = pd.to_datetime(df_work["Datetime"])

    try:
        if chart_type.lower() == "line":
            from project1_main_tab.Plot_modules.line_chart import plot_line_chart
            plot_line_chart(adapter, df_work)
        elif chart_type.lower() == "scatter":
            from project1_main_tab.Plot_modules.scatter_chart import plot_scatter_chart
            plot_scatter_chart(adapter, df_work)
        elif chart_type.lower() == "bar":
            from project1_main_tab.Plot_modules.bar_chart import plot_bar_chart
            plot_bar_chart(adapter, df_work)
        elif chart_type.lower() == "histogram":
            from project1_main_tab.Plot_modules.histogram_chart import plot_histogram_chart
            plot_histogram_chart(adapter, df_work)
        elif chart_type.lower() == "boxplot":
            from project1_main_tab.Plot_modules.boxplot_chart import plot_boxplot_chart
            plot_boxplot_chart(adapter, df_work)
        else:
            return False
    except Exception:
        return False
    return True


class ChartCellWidget(QFrame):
    """Ô chứa đồ thị - dữ liệu từ Plot tab."""
    def __init__(self, chart_config: dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.chart_config = chart_config or {}
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            ChartCellWidget {
                background: #fafbfc;
                border: 1px solid #d0d7de;
                border-radius: 8px;
            }
        """)
        self.setMinimumSize(280, 200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.figure = Figure(figsize=(4, 3))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

    def render(self, df: pd.DataFrame | None) -> None:
        """Vẽ lại đồ thị với df mới."""
        self.figure.clear()
        chart_type = self.chart_config.get("chart_type", "line")
        vars_list = self.chart_config.get("vars", [])
        if not vars_list and df is not None and not df.empty:
            numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            vars_list = numeric[:3] if len(numeric) >= 3 else numeric

        adapter = _PlotAdapter(self.figure, {"vars": vars_list, "scales": self.chart_config.get("scales", {})})
        adapter.canvas = self.canvas

        if df is not None and not df.empty and vars_list:
            try:
                if _render_chart(adapter, df, chart_type):
                    self.canvas.draw()
                    return
            except Exception:
                pass
        # Fallback: empty
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, "Chưa có dữ liệu\nLoad data tại Tab Data Analyzing", ha="center", va="center", fontsize=12)
        ax.set_axis_off()
        self.canvas.draw()
