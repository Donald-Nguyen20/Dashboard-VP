from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QDialog, QDialogButtonBox,
    QCheckBox, QLabel, QHBoxLayout, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
import numpy as np
from PySide6.QtWidgets import QDateTimeEdit
from PySide6.QtCore import QDateTime



IGNORED_COLUMNS = {'datetime', 'date', 'time', 'sourcefolder'}


class VariableSelectorDialog(QDialog):
    def __init__(self, columns, selected_vars=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn biến để vẽ")
        self.selected_vars = selected_vars or []
        self.checkboxes = []

        layout = QVBoxLayout()
        for col in columns:
            cb = QCheckBox(col)
            cb.setChecked(col in self.selected_vars)
            layout.addWidget(cb)
            self.checkboxes.append(cb)

        # --- Thêm nút Check All / Uncheck All ---
        action_layout = QHBoxLayout()
        btn_check_all = QPushButton("✅ Chọn tất cả")
        btn_uncheck_all = QPushButton("❌ Bỏ chọn tất cả")

        btn_check_all.clicked.connect(self.check_all)
        btn_uncheck_all.clicked.connect(self.uncheck_all)

        action_layout.addWidget(btn_check_all)
        action_layout.addWidget(btn_uncheck_all)
        layout.addLayout(action_layout)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.setLayout(layout)

    def get_selected_variables(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]
    
    def check_all(self):
        for cb in self.checkboxes:
            cb.setChecked(True)

    def uncheck_all(self):
        for cb in self.checkboxes:
            cb.setChecked(False)



class PlotTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_main_window = parent
        self.df = pd.DataFrame()
        self.selected_vars = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        control_layout = QHBoxLayout()

        self.btn_select_vars = QPushButton("🤍 Chọn biến")
        self.btn_select_vars.clicked.connect(self.open_variable_dialog)
        control_layout.addWidget(self.btn_select_vars)

        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["Line", "Scatter"])
        control_layout.addWidget(QLabel("Loại biểu đồ:"))
        control_layout.addWidget(self.chart_type_combo)

        self.btn_plot = QPushButton("🌐 Tuý chọn nâng cao")
        self.btn_plot.clicked.connect(self.plot_selected_variables)
        control_layout.addWidget(self.btn_plot)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        fig = Figure(figsize=(5, 4))
        self.canvas = FigureCanvas(fig)
        layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.add_subplot(111)

        self.toolbar = NavigationToolbar(self.canvas, self)  # ✅ Đặt sau khi self.canvas đã được khởi tạo
        layout.addWidget(self.toolbar)  # có thể đặt trước hoặc sau canvas tùy bạn muốn
        layout.addWidget(self.canvas)

        self.start_time_edit = QDateTimeEdit()
        self.end_time_edit = QDateTimeEdit()
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")

        self.start_time_edit.setCalendarPopup(True)
        self.end_time_edit.setCalendarPopup(True)

        control_layout.addWidget(QLabel("⏱ Từ:"))
        control_layout.addWidget(self.start_time_edit)
        control_layout.addWidget(QLabel("Đến:"))
        control_layout.addWidget(self.end_time_edit)

        self.btn_redraw = QPushButton("📈 Vẽ lại biểu đồ")
        self.btn_redraw.clicked.connect(self.plot_selected_variables)
        control_layout.addWidget(self.btn_redraw)

        

    def update_variables(self, df: pd.DataFrame):
        self.df = df
        all_plot_cols = [col for col in df.columns if col.lower() not in IGNORED_COLUMNS]
        self.selected_vars = all_plot_cols
        self.ax.clear()
        if 'Datetime' in df.columns:
            min_time = pd.to_datetime(df['Datetime'].min())
            max_time = pd.to_datetime(df['Datetime'].max())
            self.start_time_edit.setDateTime(QDateTime(min_time))
            self.end_time_edit.setDateTime(QDateTime(max_time))
            self.plot_selected_variables()

    def open_variable_dialog(self):
        if self.df.empty:
            QMessageBox.warning(self, "Cảnh báo", "Chưa có dữ liệu.")
            return

        columns = [col for col in self.df.columns if col.lower() not in IGNORED_COLUMNS]
        dialog = VariableSelectorDialog(columns, self.selected_vars or columns, self)

        if dialog.exec():
            self.selected_vars = dialog.get_selected_variables()
            self.plot_selected_variables()

    def plot_selected_variables(self):
        if not self.selected_vars:
            QMessageBox.information(self, "Thông báo", "Hãy chọn ít nhất 1 biến để vẽ.")
            return

        self.ax.clear()
            # ⏳ Lọc theo khoảng thời gian đã chọn
        if 'Datetime' in self.df.columns:
            start_dt = self.start_time_edit.dateTime().toPython()
            end_dt = self.end_time_edit.dateTime().toPython()

            df_filtered = self.df[
                (self.df['Datetime'] >= start_dt) &
                (self.df['Datetime'] <= end_dt)
            ]
        else:
            df_filtered = self.df


        chart_type = self.chart_type_combo.currentText().lower()

        if chart_type == "scatter":
            if len(self.selected_vars) != 2:
                QMessageBox.warning(self, "⚠️ Cảnh báo", "Với biểu đồ scatter, hãy chọn đúng 2 biến để vẽ.")
                return

            x_col, y_col = self.selected_vars
            if x_col not in self.df.columns or y_col not in self.df.columns:
                QMessageBox.critical(self, "Lỗi", "Biến không tồn tại trong dữ liệu.")
                return

            x = df_filtered[x_col]
            y = df_filtered[y_col]

            # Nếu cột x là datetime, cần chuyển sang số để hồi quy
            if np.issubdtype(x.dtype, np.datetime64):
                x_numeric = x.astype('int64') / 1e9  # seconds
            else:
                x_numeric = x

            mask = ~(x_numeric.isna() | y.isna())
            x_clean = x_numeric[mask]
            y_clean = y[mask]
            datetime_series = df_filtered['Datetime'][mask]  # ✅ sửa chỗ lỗi

            if len(x_clean) < 2:
                QMessageBox.warning(self, "Không đủ dữ liệu", "Không đủ điểm để vẽ hồi quy.")
                return

            try:
                coeffs = np.polyfit(x_clean, y_clean, deg=1)
                poly_eq = np.poly1d(coeffs)
                y_pred = poly_eq(x_clean)
                residuals = y_clean - y_pred
                r_squared = 1 - (np.sum(residuals**2) / np.sum((y_clean - y_clean.mean())**2))

                scatter = self.ax.scatter(x_clean, y_clean, c=np.abs(residuals),
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


        else:
            if 'Datetime' not in self.df.columns:
                QMessageBox.critical(self, "Lỗi", "Dữ liệu phải có cột 'Datetime' để vẽ biểu đồ Line.")
                return
            for col in self.selected_vars:
                if col in df_filtered.columns:
                    if chart_type == "line":
                        self.ax.plot(df_filtered['Datetime'], df_filtered[col], label=col)


            self.ax.set_xlabel("Thời gian")
            self.ax.set_ylabel("Giá trị")
            self.ax.set_title("Biểu đồ thời gian")

        self.ax.set_position([0.04, 0.03, 0.95, 0.936])
        self.canvas.draw()

        # --- Tooltip nâng cao ---
        import mplcursors
        from matplotlib.dates import num2date

        try:
            self.canvas.figure.canvas.callbacks.disconnect('motion_notify_event')
        except Exception:
            pass

        if chart_type == "line":
            cursor = mplcursors.cursor(self.ax.lines, hover=True)

            @cursor.connect("add")
            def on_add(sel):
                line = sel.artist
                var_name = line.get_label()
                x_float, y = sel.target
                x_dt = num2date(x_float)
                sel.annotation.set(
                    text=f"{var_name}\n{x_dt:%Y-%m-%d %H:%M}\n{y:.2f}"
                )
                sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)

        elif chart_type == "scatter":
            cursor = mplcursors.cursor(self.ax.collections, hover=True)

            @cursor.connect("add")
            def on_add(sel):
                index = sel.index
                x, y = sel.target
                timestamp = datetime_series.iloc[index] if index < len(datetime_series) else "N/A"
                sel.annotation.set(
                    text=f"Time: {timestamp:%Y-%m-%d %H:%M}\nX: {x:.2f}\nY: {y:.2f}"
                )
                sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)
