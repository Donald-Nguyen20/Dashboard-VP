# file: ML_TAB/Steps/Step4/line_visualization_dialog.py

from __future__ import annotations

from typing import Optional, List, Dict

import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QMessageBox,
    QDateTimeEdit,
    QDialogButtonBox,
    QLineEdit,
)

from .variable_selector_dialog import VariableSelectorDialog
from .line_plot_utils import plot_line_multi, IGNORED_COLUMNS


class DataLinePlotDialog(QDialog):
    """
    Step 4 — trực quan hóa line:
    - Combobox chọn nguồn: Raw data / Cleaned data
    - Chọn nhiều biến để overlay
    - Lọc theo Datetime nếu có
    - Dùng plot_line_multi() để vẽ
    """

    def __init__(
        self,
        raw_df: Optional[pd.DataFrame],
        cleaned_df: Optional[pd.DataFrame],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.WindowSystemMenuHint)
        self.setWindowTitle("Step 4 — Data visualization (Line)")
        self.resize(1100, 700)

        self.raw_df = raw_df
        self.cleaned_df = cleaned_df

        self.current_df: Optional[pd.DataFrame] = None
        self.plot_columns: List[str] = []
        self.selected_vars: List[str] = []
        self.scales: Dict[str, float] = {}

        main_layout = QVBoxLayout(self)

        # === HÀNG CONTROL TRÊN CÙNG ===
        control_layout = QHBoxLayout()

        # Chọn nguồn dữ liệu: Raw / Cleaned
        self.cboSource = QComboBox(self)
        self.cboSource.addItem("Raw data", userData="raw")
        self.cboSource.addItem("Cleaned data", userData="cleaned")
        control_layout.addWidget(QLabel("Source:"))
        control_layout.addWidget(self.cboSource)

        from PySide6.QtWidgets import QPushButton  # import cục bộ cho gọn

        self.btn_select_vars = QPushButton("🤍 Variables")
        self.btn_select_vars.clicked.connect(self.open_variable_dialog)
        control_layout.addWidget(self.btn_select_vars)

        # Thời gian (nếu có Datetime)
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

        # Nút vẽ
        self.btn_plot = QPushButton("📈 Draw")
        self.btn_plot.clicked.connect(self.plot_selected_variables)
        control_layout.addWidget(self.btn_plot)
        # Nút mở scale dialog
        self.btn_scale = QPushButton("🧮 Scale")
        self.btn_scale.clicked.connect(self.open_scale_dialog)
        control_layout.addWidget(self.btn_scale)

        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        # === MATPLOTLIB CANVAS + TOOLBAR ===
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        self._cid_scroll = self.canvas.mpl_connect("scroll_event", self._on_scroll)

        self.ax = self.figure.add_subplot(111)

        self.toolbar = NavigationToolbar(self.canvas, self)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas, 1)

        # Kết nối signal
        self.cboSource.currentIndexChanged.connect(self._on_source_changed)

        # Init
        self._on_source_changed()

    # ---------- Helper: lấy DF nguồn theo combobox ----------
    def _current_df_raw(self) -> Optional[pd.DataFrame]:
        mode = self.cboSource.currentData()
        if mode == "cleaned":
            return self.cleaned_df
        return self.raw_df

    # ---------- Khi đổi nguồn: chuẩn hóa DF, cột, thời gian ----------
    def _on_source_changed(self):
        df = self._current_df_raw()
        self.current_df = None
        self.plot_columns = []

        if df is None or df.empty:
            self._clear_plot()
            return

        df = df.copy()

        # Tìm cột Datetime (nếu có)
        datetime_col = None
        for col in df.columns:
            if col.lower() in ("datetime", "date_time"):
                datetime_col = col
                break

        if datetime_col is not None:
            df[datetime_col] = pd.to_datetime(df[datetime_col], errors="coerce")
            df = df.dropna(subset=[datetime_col])
            if not df.empty:
                min_time = df[datetime_col].min()
                max_time = df[datetime_col].max()
                self.start_time_edit.setDateTime(QDateTime(min_time))
                self.end_time_edit.setDateTime(QDateTime(max_time))
        else:
            now = QDateTime.currentDateTime()
            self.start_time_edit.setDateTime(now)
            self.end_time_edit.setDateTime(now)

        # Lọc cột numeric
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        numeric_cols = [c for c in numeric_cols if c.lower() not in IGNORED_COLUMNS]

        if not numeric_cols:
            self._clear_plot()
            QMessageBox.warning(self, "No numeric data", "Không tìm thấy cột số để vẽ line.")
            return

        self.current_df = df
        self.plot_columns = numeric_cols

        # Nếu chưa chọn biến -> mặc định chọn hết
        if not self.selected_vars:
            self.selected_vars = numeric_cols.copy()

        self.plot_selected_variables()

    # ---------- Dialog chọn biến ----------
    def open_variable_dialog(self):
        if self.current_df is None or not self.plot_columns:
            QMessageBox.warning(self, "Chưa có dữ liệu", "Không có dữ liệu để chọn biến.")
            return

        dlg = VariableSelectorDialog(self.plot_columns, self.selected_vars, self)
        if dlg.exec():
            self.selected_vars = dlg.get_selected_variables()
            self.plot_selected_variables()
    def open_scale_dialog(self):
        if not self.selected_vars:
            QMessageBox.warning(self, "Thông báo", "Hãy chọn biến trước!")
            return

        dlg = SimpleScaleDialog(self.selected_vars, self.scales, self)
        if dlg.exec():
            self.scales = dlg.get_scales()
            self.plot_selected_variables()

    # ---------- Xóa plot ----------
    def _clear_plot(self):
        self.figure.clear()
        self.canvas.draw_idle()

    # ---------- Vẽ line cho các biến đã chọn ----------
    def plot_selected_variables(self):
        df = self.current_df
        if df is None or df.empty:
            self._clear_plot()
            return

        if not self.selected_vars:
            QMessageBox.information(self, "Thông báo", "Hãy chọn ít nhất 1 biến để vẽ.")
            return

        # Lọc theo thời gian nếu có Datetime
        datetime_col = None
        for col in df.columns:
            if col.lower() in ("datetime", "date_time"):
                datetime_col = col
                break

        df_filtered = df
        if datetime_col is not None:
            start_dt = self.start_time_edit.dateTime().toPython()
            end_dt = self.end_time_edit.dateTime().toPython()
            mask = (df[datetime_col] >= start_dt) & (df[datetime_col] <= end_dt)
            df_filtered = df.loc[mask]
            if df_filtered.empty:
                QMessageBox.information(self, "Thông báo", "Khoảng thời gian không có dữ liệu.")
                self._clear_plot()
                return

        # Gọi hàm line riêng
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        plot_line_multi(
            ax=self.ax,
            df=df_filtered,
            variables=self.selected_vars,
            datetime_col=datetime_col,
            scales=self.scales,
            source_text=self.cboSource.currentText(),
        )

        self.canvas.draw_idle()
    def _on_scroll(self, event):
        """
        Zoom in/out khi cuộn con lăn chuột trên biểu đồ.
        - Cuộn lên: zoom in (phóng to)
        - Cuộn xuống: zoom out (thu nhỏ)
        """
        # Nếu chuột không nằm trên trục vẽ thì bỏ qua
        if event.inaxes != self.ax:
            return

        base_scale = 1.2  # hệ số zoom

        # Xác định hướng zoom
        if event.button == "up":
            scale_factor = 1 / base_scale   # zoom in
        elif event.button == "down":
            scale_factor = base_scale       # zoom out
        else:
            return

        ax = self.ax

        # Lấy tọa độ điểm mà con trỏ đang hover
        xdata = event.xdata
        ydata = event.ydata
        if xdata is None or ydata is None:
            return

        # Lấy phạm vi hiện tại
        x_left, x_right = ax.get_xlim()
        y_bottom, y_top = ax.get_ylim()

        # Tính kích thước mới theo scale
        x_range = (x_right - x_left) * scale_factor
        y_range = (y_top - y_bottom) * scale_factor

        # Tỷ lệ tương đối: thông minh, giữ điểm zoom tại vị trí trỏ chuột
        relx = (x_right - xdata) / (x_right - x_left)
        rely = (y_top - ydata) / (y_top - y_bottom)

        new_x_left = xdata - x_range * (1 - relx)
        new_x_right = xdata + x_range * relx
        new_y_bottom = ydata - y_range * (1 - rely)
        new_y_top = ydata + y_range * rely

        # Áp dụng zoom
        ax.set_xlim(new_x_left, new_x_right)
        ax.set_ylim(new_y_bottom, new_y_top)

        # Vẽ lại
        self.canvas.draw_idle()


class SimpleScaleDialog(QDialog):
    """
    Dialog (tùy chọn) để scale từng biến nếu sau này anh muốn dùng.
    Chưa gắn vào UI, nhưng để sẵn ở đây.
    """
    def __init__(self, variables: List[str], scales: Optional[Dict[str, float]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scale từng biến")
        self.scales = scales or {}
        self.edits: Dict[str, QLineEdit] = {}

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

    def get_scales(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for var, edit in self.edits.items():
            txt = edit.text().strip()
            try:
                out[var] = float(txt) if txt else 1.0
            except ValueError:
                out[var] = 1.0
        return out
