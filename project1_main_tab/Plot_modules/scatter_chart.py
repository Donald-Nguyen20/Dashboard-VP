import numpy as np
import pandas as pd
import mplcursors
from PySide6.QtWidgets import QMessageBox
from matplotlib.dates import num2date


def plot_scatter_chart(self, df_filtered):
    if len(self.selected_vars) != 2:
        QMessageBox.warning(self, "⚠️ Cảnh báo", "Với biểu đồ scatter, hãy chọn đúng 2 biến để vẽ.")
        return

    x_col, y_col = self.selected_vars
    if x_col not in self.df.columns or y_col not in self.df.columns:
        QMessageBox.critical(self, "Lỗi", "Biến không tồn tại trong dữ liệu.")
        return

    x = df_filtered[x_col]
    y = df_filtered[y_col]

    if np.issubdtype(x.dtype, np.datetime64):
        x_numeric = x.astype('int64') / 1e9
    else:
        x_numeric = x

    mask = ~(x_numeric.isna() | y.isna())
    x_clean = x_numeric[mask]
    y_clean = y[mask]
    datetime_series = df_filtered['Datetime'][mask]

    if len(x_clean) < 2:
        QMessageBox.warning(self, "Không đủ dữ liệu", "Không đủ điểm để vẽ hồi quy.")
        return

    try:
        coeffs = np.polyfit(x_clean, y_clean, deg=1)
        poly_eq = np.poly1d(coeffs)
        y_pred = poly_eq(x_clean)
        residuals = y_clean - y_pred
        r_squared = 1 - (np.sum(residuals**2) / np.sum((y_clean - y_clean.mean())**2))

        self.ax.scatter(x_clean, y_clean, c=np.abs(residuals),
                        cmap='coolwarm', alpha=0.7, label=f"{y_col} vs {x_col}")

        x_sorted = np.sort(x_clean)
        self.ax.plot(x_sorted, poly_eq(x_sorted), color='red', linestyle='--', label='Regression line')

        a, b = coeffs
        eqn = f"y = {a:.4f}x + {b:.4f}\n$R^2$ = {r_squared:.4f}"
        self.ax.text(0.05, 0.95, eqn, transform=self.ax.transAxes,
                     fontsize=10, verticalalignment='top', color='red',
                     bbox=dict(facecolor='white', alpha=0.8, edgecolor='red'))

    except Exception as e:
        print(f"Lỗi hồi quy: {e}")
        self.ax.scatter(x_clean, y_clean, label=f"{y_col} vs {x_col}", alpha=0.7)

    self.ax.set_xlabel(x_col)
    self.ax.set_ylabel(y_col)
    self.ax.set_title(f"Scatter Plot: {y_col} vs {x_col}")

    try:
        self.canvas.figure.canvas.callbacks.disconnect('motion_notify_event')
    except Exception:
        pass

    cursor = mplcursors.cursor(self.ax.collections, hover=True)

    @cursor.connect("add")
    def on_add(sel):
        index = sel.index
        x_val, y_val = sel.target
        if 0 <= index < len(datetime_series):
            timestamp = datetime_series.iat[index]
            timestamp_str = f"{timestamp:%Y-%m-%d %H:%M}"
        else:
            timestamp_str = "N/A"

        sel.annotation.set(
            text=f"⏱ {timestamp_str}\nX: {x_val:.2f}\nY: {y_val:.2f}"
        )
        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)

    self.canvas.draw()
