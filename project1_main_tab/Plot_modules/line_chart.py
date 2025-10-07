from PySide6.QtWidgets import QMessageBox
from matplotlib.dates import num2date
import mplcursors
import numpy as np
import pandas as pd



def plot_line_chart(self, df_filtered):
    if 'Datetime' not in self.df.columns:
        QMessageBox.critical(self, "Lỗi", "Thiếu cột 'Datetime'.")
        return

    self.ax.clear()
    for col in self.selected_vars:
        if col in df_filtered.columns:
            scale = self.scales.get(col, 1)
            y_plot = df_filtered[col] * scale
            self.ax.plot(df_filtered['Datetime'], y_plot, label=col)

    self.ax.set_xlabel("Thời gian")
    self.ax.set_ylabel("Giá trị (đã scale)")
    self.ax.set_title("Line Chart (Scale)")
    self.ax.set_position([0.04, 0.06, 0.957, 0.888])

    # Tooltips vẫn là giá trị gốc
    import mplcursors
    from matplotlib.dates import num2date
    cursor = mplcursors.cursor(self.ax.lines, hover=True)

    @cursor.connect("add")
    def on_add(sel):
        line = sel.artist
        var = line.get_label()
        x_float, y_plot = sel.target
        x_dt = num2date(x_float)
        idx = np.argmin(np.abs(df_filtered['Datetime'].map(pd.Timestamp.timestamp) - x_dt.timestamp()))
        y_goc = df_filtered[var].iloc[idx]
        scale = self.scales.get(var, 1)
        sel.annotation.set(text=f"{var}\n{x_dt:%Y-%m-%d %H:%M}\nGốc: {y_goc:.2f}\nScale: {scale}")
        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)

    self.canvas.draw()

