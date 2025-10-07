from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
    QHBoxLayout, QTextEdit, QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QSpacerItem
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

class VariableSelectorDialog(QDialog):
    def __init__(self, variables, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn biến để phân tích Histogram")
        self.resize(320, 340)
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(5)
        scroll_content.setMinimumWidth(220)

        self.select_all_box = QCheckBox("Chọn tất cả")
        self.select_all_box.setChecked(True)
        self.select_all_box.stateChanged.connect(self.toggle_select_all)
        scroll_layout.addWidget(self.select_all_box)

        self.checkboxes = []
        for var in variables:
            cb = QCheckBox(var)
            cb.setChecked(True)
            scroll_layout.addWidget(cb)
            self.checkboxes.append(cb)
        scroll_layout.addStretch(1)
        scroll.setWidget(scroll_content)
        scroll.setFixedHeight(220)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def toggle_select_all(self, state):
        checked = (state == Qt.Checked)
        for cb in self.checkboxes:
            cb.setChecked(checked)

    def get_selected_vars(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

class HistogramWidget(QWidget):
    def __init__(self, col, data):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 18)

        self.plot_canvas = FigureCanvas(Figure(figsize=(6.3, 2.4)))
        fig = self.plot_canvas.figure
        fig.clf()
        ax = fig.add_subplot(111)
        ax.hist(data, bins=30, edgecolor='black')
        ax.set_title(f'Histogram: {col}', fontsize=13)
        ax.set_xlabel(col, fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        fig.tight_layout()
        self.plot_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.plot_canvas.setMinimumHeight(190)
        self.plot_canvas.setMaximumHeight(280)
        layout.addWidget(self.plot_canvas)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setMinimumHeight(80)
        self.report_text.setMaximumHeight(130)
        self.report_text.setStyleSheet(
            "font-size: 15px; background: #f8fafd; border-radius: 10px; padding: 9px;"
        )
        self.report_text.setText(self.generate_histogram_report(data, col))
        layout.addWidget(self.report_text)

    def generate_histogram_report(self, data, col):
        mean = data.mean()
        median = data.median()
        std = data.std()
        skew = data.skew()
        if skew > 1:
            skew_text = "Lệch phải (right-skewed)."
        elif skew < -1:
            skew_text = "Lệch trái (left-skewed)."
        else:
            skew_text = "Phân bố gần đối xứng."
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1
        outlier_count = ((data < (q1 - 1.5 * iqr)) | (data > (q3 + 1.5 * iqr))).sum()
        report = f"""• Số lượng: {len(data)}
• Trung bình: {mean:.2f}
• Trung vị: {median:.2f}
• Độ lệch chuẩn: {std:.2f}
• Skew: {skew:.2f} ({skew_text})
• Outlier (IQR): {outlier_count}
"""
        return report

class AnalysisReportTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area lớn chứa tất cả (cho dashboard dài dọc)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(18, 12, 18, 16)
        self.scroll_layout.setSpacing(10)

        # Header trên cùng
        header_layout = QHBoxLayout()
        self.btn_analyze = QPushButton("Phân tích Histogram")
        self.btn_analyze.setStyleSheet(
            "font-weight:bold; font-size:15px; padding:7px 26px; border-radius:8px;"
        )
        self.btn_analyze.clicked.connect(self.open_variable_selector)
        header_layout.addWidget(self.btn_analyze, alignment=Qt.AlignLeft)

        self.title = QLabel("📊 Analysis Report")
        self.title.setStyleSheet("font-size: 20px; font-weight: bold; color: #245cb6; margin-left: 14px;")
        header_layout.addWidget(self.title, alignment=Qt.AlignLeft)
        header_layout.addStretch()
        self.scroll_layout.addLayout(header_layout)

        # Dashboard grid: các histogram xếp 2 cột
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(22)
        self.grid.setContentsMargins(0, 0, 0, 12)
        self.scroll_layout.addWidget(self.grid_widget)
        self.scroll_layout.addStretch(1)
        self.scroll_area.setWidget(self.scroll_content)

        self.numeric_cols = []

    def set_dataframe(self, df: pd.DataFrame):
        self.df = df
        self.numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        self.clear_dashboard()

    def clear_dashboard(self):
        # Xóa các histogram/report hiện có trong grid
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

    def open_variable_selector(self):
        if self.df is None or not self.numeric_cols:
            return
        dialog = VariableSelectorDialog(self.numeric_cols, parent=self)
        if dialog.exec() == QDialog.Accepted:
            selected_vars = dialog.get_selected_vars()
            self.show_histograms(selected_vars)

    def show_histograms(self, cols):
        self.clear_dashboard()
        if not cols:
            return
        row, colpos = 0, 0
        for idx, colname in enumerate(cols):
            if colname not in self.df.columns:
                continue
            data = self.df[colname].dropna()
            widget = HistogramWidget(colname, data)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.grid.addWidget(widget, row, colpos)
            colpos += 1
            if colpos == 2:
                row += 1
                colpos = 0
        # Nếu lẻ thì cột phải hàng cuối là spacer
        if len(cols) % 2 == 1:
            spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.grid.addItem(spacer, row, 1)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
