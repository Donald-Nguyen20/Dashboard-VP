from __future__ import annotations
import tempfile
from typing import Callable, Optional
import pandas as pd
import plotly.io as pio

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl

# import các plotly modules bạn đang dùng
from project1_main_tab.Plotly_modules.plotly_line_chart import plotly_line_chart
from project1_main_tab.Plotly_modules.plotly_scatter2d import plotly_scatter2d
from project1_main_tab.Plotly_modules.plotly_bar_max import plotly_bar_max
from project1_main_tab.Plotly_modules.plotly_histogram import plotly_histogram
from project1_main_tab.Plotly_modules.plotly_boxplot import plotly_boxplot
from project1_main_tab.Plotly_modules.plotly_violin import plotly_violin
from project1_main_tab.Plotly_modules.plotly_boxen import plotly_boxen
from project1_main_tab.Plotly_modules.plotly_heatmap import plotly_heatmap
from project1_main_tab.Plotly_modules.plotly_zscore_scatter import plotly_zscore_scatter
from project1_main_tab.Plotly_modules.plotly_pairplot import plotly_pairplot
from project1_main_tab.Plotly_modules.plotly_hist_box import plotly_hist_box
from project1_main_tab.Plotly_modules.plotly_pie import plotly_pie
from project1_main_tab.Plotly_modules.plotly_area import plotly_area
from project1_main_tab.Plotly_modules.plotly_treemap import plotly_treemap
from project1_main_tab.Plotly_modules.plotly_sunburst import plotly_sunburst
from project1_main_tab.Plotly_modules.plotly_parcoords import plotly_parcoords
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt
class ContextMenuWebView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._menu_builder = None  # function(pos)->None

    def set_menu_builder(self, fn):
        self._menu_builder = fn

    def contextMenuEvent(self, event):
        # chặn menu mặc định của web
        if callable(self._menu_builder):
            self._menu_builder(event.globalPos())
            event.accept()
            return
        super().contextMenuEvent(event)
class PlotlySpecCell(QWidget):
    """
    Cell "sống": lưu plot spec + tự render theo time range hiện tại (do Monitoring cung cấp).
    """
    def __init__(
        self,
        spec: dict,
        df_provider: Callable[[], Optional[pd.DataFrame]],
        time_provider: Callable[[], tuple[object, object]],  # (start_dt, end_dt) python datetime
        parent=None,
    ):
        super().__init__(parent)
        self.spec = spec or {}
        self.df_provider = df_provider
        self.time_provider = time_provider

        self.on_clear = None
        self.on_refresh = None

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)


        self.view = ContextMenuWebView()
        self.view.setContextMenuPolicy(Qt.DefaultContextMenu)
        root.addWidget(self.view, 1)
        def build_menu(global_pos):
            menu = QMenu(self)
            act_refresh = menu.addAction("🔄 Refresh")
            act_clear = menu.addAction("🗑️ Clear")

            chosen = menu.exec(global_pos)
            if chosen == act_refresh:
                self.rerender()
            elif chosen == act_clear:
                if callable(getattr(self, "on_clear", None)):
                    self.on_clear()

        self.view.set_menu_builder(build_menu)

        self.rerender()

    
    def rerender(self):
        df = self.df_provider() if self.df_provider else None
        if df is None or df.empty:
            return

        df2 = df.copy()
        # hỗ trợ datetime/Datetime
        if "datetime" in df2.columns and "Datetime" not in df2.columns:
            df2.rename(columns={"datetime": "Datetime"}, inplace=True)

        if "Datetime" in df2.columns:
            df2["Datetime"] = pd.to_datetime(df2["Datetime"])
            start_dt, end_dt = self.time_provider()
            df2 = df2[(df2["Datetime"] >= start_dt) & (df2["Datetime"] <= end_dt)]

        if df2.empty:
            return

        chart_type = self.spec.get("chart_type", "Line")
        selected_vars = self.spec.get("selected_vars", [])
        range_spin = int(self.spec.get("range_spin", 1))

        fig = None
        try:
            if chart_type == "Scatter":
                if len(selected_vars) == 2:
                    fig = plotly_scatter2d(df2, selected_vars[0], selected_vars[1])

            elif chart_type == "Line":
                x = "Datetime" if "Datetime" in df2.columns else (selected_vars[0] if selected_vars else "x")
                # Monitoring chỉ áp 1 range time chung -> không gọi MultiRangeDialog
                fig = plotly_line_chart(df2, x, selected_vars, time_ranges=None)

            elif chart_type == "Bar (Max)":
                fig = plotly_bar_max(df2, selected_vars, title="Max value (in time range)", time_ranges=None)

            elif chart_type == "Area":
                x = "Datetime" if "Datetime" in df2.columns else (selected_vars[0] if selected_vars else None)
                y_cols = [c for c in selected_vars if c in df2.columns and c != x and pd.api.types.is_numeric_dtype(df2[c])]
                if x and y_cols:
                    fig = plotly_area(df2, x, y_cols)

            elif chart_type == "Histogram":
                fig = plotly_histogram(df2, selected_vars)
            elif chart_type == "Boxplot":
                fig = plotly_boxplot(df2, selected_vars)
            elif chart_type == "Violin":
                fig = plotly_violin(df2, selected_vars)
            elif chart_type == "Boxen":
                fig = plotly_boxen(df2, selected_vars)
            elif chart_type == "Histogram + Boxplot":
                fig = plotly_hist_box(df2, selected_vars)
            elif chart_type == "Heatmap Correlation":
                if len(selected_vars) >= 2:
                    fig = plotly_heatmap(df2, selected_vars)
            elif chart_type == "Z-score Scatter":
                if len(selected_vars) == 2:
                    fig = plotly_zscore_scatter(df2, selected_vars[0], selected_vars[1])
            elif chart_type == "Pairplot":
                if len(selected_vars) >= 2:
                    fig = plotly_pairplot(df2, selected_vars)
            elif chart_type == "Pie":
                fig = plotly_pie(df2, selected_vars)
            elif chart_type == "Treemap":
                fig = plotly_treemap(df2, selected_vars)
            elif chart_type == "Sunburst":
                fig = plotly_sunburst(df2, selected_vars)
            elif chart_type == "Parallel Coordinates":
                if len(selected_vars) >= 2:
                    fig = plotly_parcoords(df2, selected_vars)
        except Exception:
            fig = None

        if fig is None:
            return

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        pio.write_html(
            fig,
            file=tmp.name,
            include_plotlyjs=True,
            full_html=True,
            auto_open=False,
            config={"responsive": True, "displayModeBar": True, "scrollZoom": True, "displaylogo": False},
        )
        self.view.load(QUrl.fromLocalFile(tmp.name))