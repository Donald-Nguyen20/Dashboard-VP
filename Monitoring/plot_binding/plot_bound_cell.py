from __future__ import annotations
from typing import Callable, Optional
import pandas as pd

from PySide6.QtWidgets import QFrame, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from Monitoring.plot_binding.plot_spec import PlotSpec
from Monitoring.plot_binding.plot_renderer import render_plot

class PlotBoundCell(QFrame):
    def __init__(self, plot_spec: dict, df_provider: Callable[[], pd.DataFrame | None], parent: Optional[QFrame] = None):
        super().__init__(parent)
        self.plot_spec = plot_spec or {}
        self.df_provider = df_provider

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.figure = Figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        layout.addWidget(self.canvas, 1)

        self.render_now()

    def render_now(self):
        df = self.df_provider() if self.df_provider else None
        if df is None or df.empty:
            self.ax.clear()
            self.ax.text(0.5, 0.5, "Chưa có dữ liệu", ha="center", va="center")
            self.canvas.draw_idle()
            return
        spec = PlotSpec.from_dict(self.plot_spec)
        render_plot(self.ax, self.canvas, df, spec)