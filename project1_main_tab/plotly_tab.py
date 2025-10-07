from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFormLayout, QSplitter, QDateTimeEdit,
    QMessageBox, QDialog, QDialogButtonBox, QCheckBox, QScrollArea
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QDateTime
import pandas as pd
import plotly.io as pio
import plotly.graph_objs as go


from project1_main_tab.Plotly_modules.plotly_scatter2d import plotly_scatter2d
from project1_main_tab.Plotly_modules.plotly_line_chart import plotly_line_chart

IGNORED_COLUMNS = {'datetime', 'date', 'time', 'sourcefolder'}

class VariableSelectorDialog(QDialog):
    def __init__(self, columns, selected_vars=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn biến để vẽ")
        self.selected_vars = selected_vars or []
        self.checkboxes = []

        layout = QVBoxLayout(self)
        self.setMinimumSize(400, 800)
        checkbox_widget = QWidget()
        checkbox_layout = QVBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(4, 4, 4, 4)
        checkbox_layout.setSpacing(2)

        for col in columns:
            cb = QCheckBox(col)
            cb.setChecked(col in self.selected_vars)
            checkbox_layout.addWidget(cb)
            self.checkboxes.append(cb)
        checkbox_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(checkbox_widget)
        scroll.setMinimumHeight(200)
        scroll.setMaximumHeight(800)

        layout.addWidget(scroll)

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

class PlotlyTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = pd.DataFrame()
        self.selected_vars = []
        self.setLayout(QVBoxLayout())

        # === Top controls
        topbar = QHBoxLayout()
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["Scatter", "Line"])
        self.btn_variable = QPushButton("🧩 Variable")
        self.btn_variable.clicked.connect(self.open_variable_dialog)

        self.start_time = QDateTimeEdit()
        self.end_time = QDateTimeEdit()
        for dt in [self.start_time, self.end_time]:
            dt.setDisplayFormat("yyyy-MM-dd HH:mm")
            dt.setCalendarPopup(True)

        btn_plot = QPushButton("📊 Vẽ")
        btn_plot.clicked.connect(self.draw_chart)

        topbar.addWidget(QLabel("Biểu đồ:"))
        topbar.addWidget(self.chart_type_combo)
        topbar.addWidget(self.btn_variable)
        topbar.addWidget(QLabel("⏱ From:"))
        topbar.addWidget(self.start_time)
        topbar.addWidget(QLabel("To:"))
        topbar.addWidget(self.end_time)
        topbar.addStretch()
        topbar.addWidget(btn_plot)
        self.layout().addLayout(topbar)

        # === Plot view
        self.plot_view = QWebEngineView()
        self.layout().addWidget(self.plot_view)

    def update_plot(self, df: pd.DataFrame):
        self.df = df.copy()

        if 'Datetime' in self.df.columns:
            self.df['Datetime'] = pd.to_datetime(self.df['Datetime'])
            self.start_time.setDateTime(QDateTime(self.df['Datetime'].min()))
            self.end_time.setDateTime(QDateTime(self.df['Datetime'].max()))

        all_plot_cols = [col for col in self.df.columns if col.lower() not in IGNORED_COLUMNS]
        self.selected_vars = [col for col in self.selected_vars if col in all_plot_cols]

    def open_variable_dialog(self):
        if self.df.empty:
            QMessageBox.warning(self, "Cảnh báo", "Chưa có dữ liệu.")
            return

        columns = [col for col in self.df.columns if col.lower() not in IGNORED_COLUMNS]
        dialog = VariableSelectorDialog(columns, self.selected_vars or columns, self)

        if dialog.exec():
            self.selected_vars = dialog.get_selected_variables()
            self.draw_chart()

    def get_filtered_df(self):
        df_filtered = self.df.copy()
        if 'Datetime' in df_filtered.columns:
            start_dt = self.start_time.dateTime().toPython()
            end_dt = self.end_time.dateTime().toPython()
            df_filtered = df_filtered[
                (df_filtered['Datetime'] >= start_dt) &
                (df_filtered['Datetime'] <= end_dt)
            ]
        return df_filtered

    def draw_chart(self):
        df_filtered = self.get_filtered_df()
        chart_type = self.chart_type_combo.currentText()

        if not self.selected_vars:
            QMessageBox.warning(self, "Thiếu biến", "Chọn ít nhất 1 biến để vẽ.")
            return
        if df_filtered.empty:
            QMessageBox.warning(self, "Không có dữ liệu", "Không có dữ liệu trong khoảng thời gian.")
            return

        fig = None
        if chart_type == "Scatter":
            for i in range(len(self.selected_vars) - 1):
                fig = plotly_scatter2d(df_filtered, self.selected_vars[i], self.selected_vars[i+1])
        elif chart_type == "Line":
            x = 'Datetime'
            plotly_line_chart(df_filtered, x, self.selected_vars)  # tất cả biến gộp chung
            return



        if fig:
            html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
            self.plot_view.setHtml(html)
