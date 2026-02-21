from PySide6.QtWidgets import QMessageBox
from matplotlib.dates import num2date
import mplcursors
import numpy as np
import pandas as pd
import matplotlib.colors as mcolors


def _get_range_colors(n_ranges):
    """Generate distinct colors for n ranges"""
    if n_ranges == 1:
        return ['#1976d2']
    elif n_ranges == 2:
        return ['#1976d2', '#d32f2f']
    elif n_ranges == 3:
        return ['#1976d2', '#d32f2f', '#388e3c']
    elif n_ranges == 4:
        return ['#1976d2', '#d32f2f', '#388e3c', '#f57c00']
    else:
        cmap = mcolors.get_cmap('tab10')
        return [mcolors.rgb2hex(cmap(i % 10)) for i in range(n_ranges)]


def plot_line_chart(self, df_filtered, time_ranges=None):
    """Plot line chart with optional multiple time ranges
    
    Args:
        self: Reference to PlotTab instance
        df_filtered: DataFrame to plot (filtered by default time range)
        time_ranges: List of (start_dt, end_dt) tuples for multi-range comparison, or None
    """
    if 'Datetime' not in self.df.columns:
        QMessageBox.critical(self, "Lỗi", "Thiếu cột 'Datetime'.")
        return

    self.ax.clear()
    
    # Multi-range mode: plot lines for each time range with different colors
    if time_ranges is not None and len(time_ranges) > 1:
        colors = _get_range_colors(len(time_ranges))
        
        for range_idx, (start_dt, end_dt) in enumerate(time_ranges):
            df_range = self.df[(self.df['Datetime'] >= start_dt) & (self.df['Datetime'] <= end_dt)]
            if df_range.empty:
                continue
            
            color = colors[range_idx]
            label_suffix = f" ({start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')})"
            
            for col in self.selected_vars:
                if col in df_range.columns:
                    scale = self.scales.get(col, 1)
                    y_plot = df_range[col] * scale
                    self.ax.plot(df_range['Datetime'], y_plot, 
                                label=col + label_suffix, color=color, linewidth=2)
        
        self.ax.set_xlabel("Thời gian")
        self.ax.set_ylabel("Giá trị (đã scale)")
        self.ax.set_title("Line Chart - Multiple Ranges (Scale)")
        self.ax.set_position([0.04, 0.06, 0.957, 0.888])
        self.ax.legend(loc='best', fontsize=8)
        self.canvas.draw()
        return
    
    # Original single-range logic
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

