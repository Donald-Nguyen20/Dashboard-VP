import numpy as np
import mplcursors
from PySide6.QtWidgets import QMessageBox


def plot_modified_zscore_scatter(self, df_filtered):
    if len(self.selected_vars) != 2:
        QMessageBox.warning(self, "⚠️ Cảnh báo", "Với biểu đồ Z-score scatter, hãy chọn đúng 2 biến để vẽ.")
        return

    x_col, y_col = self.selected_vars
    if x_col not in df_filtered.columns or y_col not in df_filtered.columns:
        QMessageBox.critical(self, "Lỗi", "Biến không tồn tại trong dữ liệu.")
        return

    x = df_filtered[x_col].dropna()
    y = df_filtered[y_col].dropna()
    mask = ~(x.isna() | y.isna())
    x = x[mask]
    y = y[mask]
    
    median_y = np.median(y)
    mad_y = np.median(np.abs(y - median_y))
    
    if mad_y == 0:
        QMessageBox.warning(self, "Không thể tính MAD", "MAD bằng 0, không thể phát hiện outlier.")
        return

    modified_z = 0.6745 * (y - median_y) / mad_y
    is_outlier = np.abs(modified_z) > 3.5

    self.ax.scatter(x[~is_outlier], y[~is_outlier], label='Normal', alpha=0.7)
    self.ax.scatter(x[is_outlier], y[is_outlier], color='red', label='Outlier', marker='x')

    self.ax.set_xlabel(x_col)
    self.ax.set_ylabel(y_col)
    self.ax.set_title("Modified Z-score Scatter Plot")
    self.ax.legend()

    try:
        self.canvas.figure.canvas.callbacks.disconnect('motion_notify_event')
    except Exception:
        pass

    cursor = mplcursors.cursor(self.ax.collections, hover=True)

    @cursor.connect("add")
    def on_add(sel):
        idx = sel.index
        x_val, y_val = sel.target
        label = 'Outlier' if is_outlier.iloc[idx] else 'Normal'
        sel.annotation.set(text=f"{label}\nX: {x_val:.2f}\nY: {y_val:.2f}")
        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)

    self.canvas.draw()
