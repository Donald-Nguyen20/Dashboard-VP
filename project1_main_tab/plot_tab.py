from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QDialog, QDialogButtonBox,
    QCheckBox, QLabel, QHBoxLayout, QMessageBox, QComboBox, QScrollArea
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
import numpy as np
from PySide6.QtWidgets import QDateTimeEdit
from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QLineEdit





IGNORED_COLUMNS = {'datetime', 'date', 'time', 'sourcefolder'}


class VariableSelectorDialog(QDialog):
    def __init__(self, columns, selected_vars=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn biến để vẽ")
        self.selected_vars = selected_vars or []
        self.checkboxes = []

        layout = QVBoxLayout(self)
        self.setMinimumSize(400, 800)
        # Tạo widget chứa các checkbox
        checkbox_widget = QWidget()
        checkbox_layout = QVBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(4, 4, 4, 4)
        checkbox_layout.setSpacing(2)

        for col in columns:
            cb = QCheckBox(col)
            cb.setChecked(col in self.selected_vars)
            checkbox_layout.addWidget(cb)
            self.checkboxes.append(cb)
        checkbox_layout.addStretch()  # Đẩy các checkbox lên trên

        # Gắn vào QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(checkbox_widget)
        scroll.setMinimumHeight(200)
        scroll.setMaximumHeight(800)

        layout.addWidget(scroll)

        # Các nút Check All/Uncheck All và OK/Cancel giữ nguyên
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



    def get_selected_variables(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]
    
    def check_all(self):
        for cb in self.checkboxes:
            cb.setChecked(True)

    def uncheck_all(self):
        for cb in self.checkboxes:
            cb.setChecked(False)

from project1_main_tab.Plot_modules.scatter_chart import plot_scatter_chart
from project1_main_tab.Plot_modules.line_chart import plot_line_chart
from project1_main_tab.Plot_modules.plot_modified_zscore_scatter import plot_modified_zscore_scatter
from project1_main_tab.Plot_modules.heatmap_correlation import HeatmapDialog
from project1_main_tab.Plot_modules.histogram_chart import plot_histogram_chart
from project1_main_tab.Plot_modules.boxplot_chart import plot_boxplot_chart
from project1_main_tab.Plot_modules.hist_box_chart import plot_hist_box_chart
from project1_main_tab.Plot_modules.violin_chart import plot_violin_chart
from project1_main_tab.Plot_modules.boxen_chart import plot_boxenplot_chart
from project1_main_tab.Plot_modules.pairplot_chart import plot_pairplot_chart





class PlotTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_main_window = parent
        self.df = pd.DataFrame()
        self.selected_vars = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        control_layout = QHBoxLayout()
        self.hue_combo = QComboBox()
        self.hue_combo.addItem("❌ Không phân loại")
        control_layout.addWidget(QLabel("Phân loại:"))
        control_layout.addWidget(self.hue_combo)

        self.btn_select_vars = QPushButton("🤍 Variable")
        self.btn_select_vars.clicked.connect(self.open_variable_dialog)
        control_layout.addWidget(self.btn_select_vars)

        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["Line", "Scatter", "Z-score Scatter", "Heatmap Correlation", 
                                        "Histogram", "Boxplot", "Histogram + Boxplot", 
                                        "Violin", "Boxen","Pairplot"])
        control_layout.addWidget(QLabel("Plot:"))
        control_layout.addWidget(self.chart_type_combo)

        self.btn_plot = QPushButton("🌐 Select")
        self.btn_plot.clicked.connect(self.plot_selected_variables)
        control_layout.addWidget(self.btn_plot)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        fig = Figure(figsize=(5, 4))
        self.figure = fig  
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

        control_layout.addWidget(QLabel("⏱ From:"))
        control_layout.addWidget(self.start_time_edit)
        control_layout.addWidget(QLabel("To:"))
        control_layout.addWidget(self.end_time_edit)

        self.btn_redraw = QPushButton("📈 Drawing")
        self.btn_redraw.clicked.connect(self.plot_selected_variables)
        control_layout.addWidget(self.btn_redraw)

        self.btn_scale = QPushButton("🧮 Scale")
        self.btn_scale.clicked.connect(self.open_scale_dialog)
        control_layout.addWidget(self.btn_scale)

        self.scales = {}  # trong __init__ của PlotTab

    def open_scale_dialog(self):
        if not self.selected_vars:
            QMessageBox.warning(self, "Thông báo", "Hãy chọn biến!")
            return
        dlg = SimpleScaleDialog(self.selected_vars, self.scales, self)
        if dlg.exec():
            self.scales = dlg.get_scales()
            self.plot_selected_variables()


    def update_variables(self, df: pd.DataFrame):
        self.df = df

        if 'Datetime' in df.columns:
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            min_time = df['Datetime'].min()
            max_time = df['Datetime'].max()
            self.start_time_edit.setDateTime(QDateTime(min_time))
            self.end_time_edit.setDateTime(QDateTime(max_time))
            df['Month'] = df['Datetime'].dt.month_name()

        if 'NET MW' in df.columns:
            def classify_mw_level(mw):
                if 250.8 <= mw <= 277.2:
                    return "264MW"
                elif 627 <= mw <= 693:
                    return "660MW"
                else:
                    return "Other"
            df['Level_Mw'] = df['NET MW'].apply(classify_mw_level)

        all_plot_cols = [col for col in df.columns if col.lower() not in IGNORED_COLUMNS]

        # 🧠 Giữ lại trạng thái biến đã được chọn trước đó
        self.selected_vars = [col for col in self.selected_vars if col in all_plot_cols]

        self.hue_combo.clear()
        self.hue_combo.addItem("❌ Không phân loại")
        self.hue_combo.addItems(["Month", "Level_Mw"])

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
        self.figure.clear()         # Xóa toàn bộ các subplot/axes cũ
        self.ax = self.figure.add_subplot(111)  # Tạo lại 1 axes mặc định cho các plot khác

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

        if chart_type == "line":
            plot_line_chart(self, df_filtered)
        elif chart_type == "scatter":
            plot_scatter_chart(self, df_filtered)
        elif chart_type == "z-score scatter":
            plot_modified_zscore_scatter(self, df_filtered)
        elif chart_type == "heatmap correlation":
            try:
                dlg = HeatmapDialog(df_filtered, self.selected_vars, parent=self)
                dlg.exec()
            except ValueError as e:
                QMessageBox.warning(self, "Không thể vẽ Heatmap", str(e))
        elif chart_type == "histogram":
            plot_histogram_chart(self, df_filtered)
        elif chart_type == "boxplot":
            plot_boxplot_chart(self, df_filtered)
        elif chart_type == "histogram + boxplot":
            plot_hist_box_chart(self, df_filtered)
        elif chart_type == "violin":
            plot_violin_chart(self, df_filtered)
        elif chart_type == "boxen":
            plot_boxenplot_chart(self, df_filtered)
        elif chart_type == "pairplot":
            plot_pairplot_chart(self, df_filtered)

        else:
            QMessageBox.warning(self, "Chưa hỗ trợ", f"Chưa hỗ trợ kiểu biểu đồ: {chart_type}")



class SimpleScaleDialog(QDialog):
    def __init__(self, variables, scales=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scale từng biến")
        self.scales = scales or {}
        self.edits = {}
        layout = QVBoxLayout(self)
        for var in variables:
            row = QHBoxLayout()
            row.addWidget(QLabel(var))
            edit = QLineEdit(str(self.scales.get(var, 1)))
            row.addWidget(edit)
            layout.addLayout(row)
            self.edits[var] = edit
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_scales(self):
        return {var: float(edit.text() or 1) for var, edit in self.edits.items()}