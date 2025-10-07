# Plot_modules/hist_box_chart.py

import numpy as np
import pandas as pd
from PySide6.QtWidgets import QMessageBox

def plot_hist_box_chart(plot_tab, df):
    selected = plot_tab.selected_vars
    if not selected:
        QMessageBox.warning(plot_tab, "Cảnh báo", "Hãy chọn ít nhất 1 biến để vẽ.")
        return

    num_vars = len(selected)
    ncols = num_vars
    nrows = 2

    plot_tab.figure.clear()
    axes = plot_tab.figure.subplots(nrows, ncols, squeeze=False)

    for idx, col in enumerate(selected):
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            data = df[col].dropna()

            # Histogram ở hàng 0
            ax_hist = axes[0][idx]
            ax_hist.hist(data, bins=30, color="#90caf9", edgecolor='black', alpha=0.8)
            ax_hist.set_title(col)
            ax_hist.set_xlabel("")
            ax_hist.set_ylabel("Tần suất")

            # Boxplot ở hàng 1 (dùng config chuẩn giống boxplot đơn lẻ)
            ax_box = axes[1][idx]
            ax_box.boxplot(
                data, vert=False, patch_artist=True,
                boxprops=dict(facecolor='#afd8ff', color='#0d3054'),
                medianprops=dict(color='#ff4e00', linewidth=2),
                flierprops=dict(marker='o', markerfacecolor='red', markersize=6, linestyle='none')
            )
            ax_box.set_xlabel("Giá trị")
            ax_box.get_yaxis().set_visible(False)
            ax_box.set_ylabel("")
        else:
            axes[0][idx].set_visible(False)
            axes[1][idx].set_visible(False)

    plot_tab.figure.tight_layout()
    plot_tab.canvas.draw()
    plot_tab.ax = axes[0][0]
