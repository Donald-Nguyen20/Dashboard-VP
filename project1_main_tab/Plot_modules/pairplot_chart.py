# File: Plot_modules/pairplot_chart.py

import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
from PySide6.QtWidgets import QMessageBox

# Biến toàn cục để theo dõi figure pairplot trước đó
previous_pairplot_fig = None

def plot_pairplot_chart(plot_tab, df):
    global previous_pairplot_fig

    selected = plot_tab.selected_vars
    if not selected or len(selected) < 2:
        QMessageBox.warning(plot_tab, "Cảnh báo", "Hãy chọn ít nhất 2 biến để vẽ pairplot.")
        return

    selected_numeric = [col for col in selected if pd.api.types.is_numeric_dtype(df[col])]
    if len(selected_numeric) < 2:
        QMessageBox.warning(plot_tab, "Cảnh báo", "Cần ít nhất 2 biến số để vẽ pairplot.")
        return

    # Lọc theo thời gian nếu có
    if 'Datetime' in df.columns:
        start_dt = plot_tab.start_time_edit.dateTime().toPython()
        end_dt = plot_tab.end_time_edit.dateTime().toPython()
        df = df[(df['Datetime'] >= start_dt) & (df['Datetime'] <= end_dt)]

    # Lấy hue (cột phân loại) nếu có
    hue_col = plot_tab.hue_combo.currentText()
    if hue_col == "❌ Không phân loại":
        hue_col = None

    # Đóng biểu đồ cũ nếu có
    if previous_pairplot_fig is not None:
        plt.close(previous_pairplot_fig)

    # Vẽ biểu đồ pairplot
    pair_fig = sns.pairplot(
        df,
        vars=selected_numeric,
        hue=hue_col,
        diag_kind='kde',
        corner=True
    )
    pair_fig.fig.suptitle("Pairplot giữa các biến đã chọn", y=1.02)
    previous_pairplot_fig = pair_fig.fig
    plt.show()
