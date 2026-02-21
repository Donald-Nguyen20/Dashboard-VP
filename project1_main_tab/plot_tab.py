from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QDialog, QDialogButtonBox,
    QCheckBox, QLabel, QHBoxLayout, QMessageBox, QComboBox, QScrollArea, QSpinBox
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
from PySide6.QtCore import Signal
from Monitoring.plot_binding.plot_spec import PlotSpec

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
        checkbox_layout.addStretch()

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


class MultiRangeDialog(QDialog):
    """Dialog để nhập nhiều khoảng thời gian cho Bar chart comparison"""
    def __init__(self, num_ranges=2, df=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn khoảng thời gian cho từng Range")
        self.num_ranges = num_ranges
        self.date_pickers = []
        
        # Calculate default date ranges (3 days each, going backwards)
        default_ranges = self._calculate_default_ranges(df, num_ranges)
        
        layout = QVBoxLayout(self)
        
        for i in range(num_ranges):
            # Row for each range
            row_layout = QHBoxLayout()
            row_layout.addWidget(QLabel(f"Range {i+1}:"))
            
            # Start date
            start_edit = QDateTimeEdit()
            start_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
            start_edit.setCalendarPopup(True)
            if default_ranges[i] is not None:
                start_edit.setDateTime(default_ranges[i][0])
            row_layout.addWidget(QLabel("From:"))
            row_layout.addWidget(start_edit)
            
            # End date
            end_edit = QDateTimeEdit()
            end_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
            end_edit.setCalendarPopup(True)
            if default_ranges[i] is not None:
                end_edit.setDateTime(default_ranges[i][1])
            row_layout.addWidget(QLabel("To:"))
            row_layout.addWidget(end_edit)
            
            self.date_pickers.append((start_edit, end_edit))
            layout.addLayout(row_layout)
        
        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
        self.setMinimumWidth(800)
    
    def _calculate_default_ranges(self, df, num_ranges):
        """Calculate default date ranges (3 days each, going backwards from most recent)"""
        if df is None or df.empty or 'Datetime' not in df.columns:
            from datetime import datetime, timedelta
            # Fallback: use current time
            now = datetime.now()
            ranges = []
            for i in range(num_ranges):
                end = now - timedelta(days=i*3)
                start = end - timedelta(days=3)
                ranges.append((start, end))
            return ranges
        
        from datetime import timedelta
        max_date = pd.to_datetime(df['Datetime']).max()
        ranges = []
        
        for i in range(num_ranges):
            # Calculate start and end for this range (3 days each)
            range_end = max_date - timedelta(days=i*3)
            range_start = range_end - timedelta(days=3)
            ranges.append((range_start, range_end))
        
        return ranges
    
    def get_ranges(self):
        """Returns list of (start_datetime, end_datetime) tuples"""
        ranges = []
        for start_edit, end_edit in self.date_pickers:
            start_dt = start_edit.dateTime().toPython()
            end_dt = end_edit.dateTime().toPython()
            ranges.append((start_dt, end_dt))
        return ranges



from project1_main_tab.Plot_modules.line_chart import plot_line_chart
from project1_main_tab.Plot_modules.scatter_chart import plot_scatter_chart
from project1_main_tab.Plot_modules.plot_modified_zscore_scatter import plot_modified_zscore_scatter
from project1_main_tab.Plot_modules.heatmap_correlation import HeatmapDialog
from project1_main_tab.Plot_modules.histogram_chart import plot_histogram_chart
from project1_main_tab.Plot_modules.boxplot_chart import plot_boxplot_chart
from project1_main_tab.Plot_modules.hist_box_chart import plot_hist_box_chart
from project1_main_tab.Plot_modules.violin_chart import plot_violin_chart
from project1_main_tab.Plot_modules.boxen_chart import plot_boxenplot_chart
from project1_main_tab.Plot_modules.pairplot_chart import plot_pairplot_chart
from project1_main_tab.Plot_modules.bar_chart import plot_bar_chart


class PlotTab(QWidget):
    plotSpecChanged = Signal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_plot_spec = None
        self._last_time_ranges = None
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
        self.chart_type_combo.addItems(["Line", "Scatter", "Bar", "Z-score Scatter", "Heatmap Correlation", 
                "Histogram", "Boxplot", "Histogram + Boxplot", 
                "Violin", "Boxen","Pairplot"])
        control_layout.addWidget(QLabel("Plot:"))
        control_layout.addWidget(self.chart_type_combo)

        # Color picker for Bar only (hidden until Bar is selected)
        self.btn_color = QPushButton("🎨 Bar Color")
        self.btn_color.clicked.connect(lambda: self._choose_color())
        # default color for bars
        self.bar_color = "#1976d2"
        self.btn_color.setVisible(False)
        control_layout.addWidget(self.btn_color)

        # Range spinbox for Bar/Line charts (hidden until Bar/Line is selected)
        self.range_spin = QSpinBox()
        self.range_spin.setMinimum(1)
        self.range_spin.setMaximum(10)
        self.range_spin.setValue(1)
        self.range_spin.setVisible(False)
        control_layout.addWidget(QLabel("Range:"))
        control_layout.addWidget(self.range_spin)

        # show/hide color button and range spinbox when chart type changes
        self.chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)

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

        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
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

        self.scales = {}

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

    def _choose_color(self):
        from PySide6.QtWidgets import QColorDialog
        col = QColorDialog.getColor()
        if col.isValid():
            # store as hex string
            self.bar_color = col.name()
            # trigger redraw to apply color
            self.plot_selected_variables()

    def _on_chart_type_changed(self, text: str):
        # show the color picker and range spinbox when selected chart type
        try:
            is_bar = text.lower() == 'bar'
            is_line = text.lower() == 'line'
        except Exception:
            is_bar = False
            is_line = False
        self.btn_color.setVisible(is_bar)
        self.range_spin.setVisible(is_bar or is_line)

    def plot_selected_variables(self):
        if not self.selected_vars:
            QMessageBox.information(self, "Thông báo", "Hãy chọn ít nhất 1 biến để vẽ.")
            return
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        chart_type = self.chart_type_combo.currentText().lower()
        
        # Special handling for Bar/Line chart with multiple ranges
        if (chart_type == "bar" or chart_type == "line") and self.range_spin.value() > 1:
            num_ranges = self.range_spin.value()
            dlg = MultiRangeDialog(num_ranges, df=self.df, parent=self)
            if dlg.exec():
                time_ranges = dlg.get_ranges()
                self._last_time_ranges = time_ranges

                if chart_type == "bar":
                    plot_bar_chart(self, self.df, time_ranges=time_ranges)
                else:
                    plot_line_chart(self, self.df, time_ranges=time_ranges)

                self._publish_plot_spec(chart_type)  # ✅ đặt vào trong if
            return
        
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

        if chart_type == "line":
            plot_line_chart(self, df_filtered)
        elif chart_type == "scatter":
            plot_scatter_chart(self, df_filtered)
        elif chart_type == "bar":
            plot_bar_chart(self, df_filtered)
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
       # ✅ thêm
        if chart_type in ("line", "scatter", "bar"):
            self._last_time_ranges = None
            self._publish_plot_spec(chart_type)
    def get_current_plot_spec(self):
        """Monitoring sẽ gọi hàm này để lấy cấu hình plot hiện tại (dict)."""
        return self._current_plot_spec

    def _publish_plot_spec(self, chart_type: str):
        """Gói cấu hình plot hiện tại thành PlotSpec -> dict và phát signal."""
        # 1) single range (nếu UI có start/end)
        start_iso = None
        end_iso = None
        if hasattr(self, "start_time_edit") and hasattr(self, "end_time_edit"):
            start_iso = self.start_time_edit.dateTime().toPython().isoformat()
            end_iso = self.end_time_edit.dateTime().toPython().isoformat()

        # 2) multi-range (nếu có)
        time_ranges_iso = None
        if self._last_time_ranges:
            time_ranges_iso = [(a.isoformat(), b.isoformat()) for a, b in self._last_time_ranges]

        # 3) lấy selected vars + hue + scales + bar_color từ PlotTab hiện tại
        spec = PlotSpec(
            chart_type=chart_type,
            selected_vars=list(getattr(self, "selected_vars", [])),
            hue=self.hue_combo.currentText() if hasattr(self, "hue_combo") else "❌ Không phân loại",
            bar_color=getattr(self, "bar_color", None),
            scales=dict(getattr(self, "scales", {}) or {}),
            start_dt_iso=start_iso,
            end_dt_iso=end_iso,
            time_ranges_iso=time_ranges_iso,
        )

        self._current_plot_spec = spec.to_dict()
        self.plotSpecChanged.emit(self._current_plot_spec)
class SimpleScaleDialog(QDialog):
    def __init__(self, variables, scales=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scale từng biến")
        self.scales = scales or {}
        self.edits = {}

        layout = QVBoxLayout(self)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(4)

        for var in variables:
            row = QHBoxLayout()
            row.addWidget(QLabel(var))
            edit = QLineEdit(str(self.scales.get(var, 1)))
            row.addWidget(edit)
            form_layout.addLayout(row)
            self.edits[var] = edit

        scroll.setWidget(container)
        layout.addWidget(scroll)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_scales(self):
        return {var: float(edit.text() or 1) for var, edit in self.edits.items()}
