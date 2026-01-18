# file: project1_main_tab/Drift_modules/drift_trend_mk.py

from __future__ import annotations

from typing import List

import pandas as pd
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QSplitter,
    QMessageBox,
    QWidget,
    QSizePolicy,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import pymannkendall as mk


class TrendOverviewDialog(QDialog):
    """
    Dialog quét Mann–Kendall cho tất cả cột numeric trong df (đã lọc),
    hiển thị bảng summary ở trên và plot trend cho 1 biến ở dưới.
    """

    def __init__(self, df: pd.DataFrame, time_col: str = "Datetime", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trend (Mann–Kendall)")
        self.resize(1100, 700)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )

        self._orig_df = df.copy()
        self.time_col = time_col

        if self.time_col not in self._orig_df.columns:
            QMessageBox.warning(self, "Trend (Mann–Kendall)",
                                f"Không tìm thấy cột thời gian '{self.time_col}' trong DataFrame.")
            self.close()
            return

        # đảm bảo kiểu Datetime
        self._orig_df[self.time_col] = pd.to_datetime(self._orig_df[self.time_col])

        self._current_window_df = self._orig_df  # sẽ cập nhật theo months
        self._feature_names: List[str] = []

        self._build_ui()
        self._run_scan()  # scan lần đầu (mặc định 6 tháng)

    # ================= UI =================

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # --- dòng control: số tháng + chọn feature ---
        control_layout = QHBoxLayout()

        lbl_months = QLabel("Số tháng gần nhất:")
        self.spin_months = QSpinBox()
        self.spin_months.setRange(1, 60)
        self.spin_months.setValue(6)  # mặc định 6 tháng
        self.spin_months.valueChanged.connect(self._run_scan)

        control_layout.addWidget(lbl_months)
        control_layout.addWidget(self.spin_months)

        control_layout.addSpacing(20)

        lbl_feat = QLabel("Biến hiển thị trend:")
        self.cb_feature = QComboBox()
        self.cb_feature.currentTextChanged.connect(self._update_plot)

        control_layout.addWidget(lbl_feat)
        control_layout.addWidget(self.cb_feature)
        control_layout.addStretch()

        main_layout.addLayout(control_layout)

        # --- splitter dọc: trên = bảng, dưới = plot ---
        splitter = QSplitter()
        splitter.setOrientation(Qt.Vertical)
        main_layout.addWidget(splitter, stretch=1)

        # bảng summary
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Feature", "Trend", "Mức độ", "Tau", "p-value", "Số điểm"]
        )
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.cellClicked.connect(self._on_table_clicked)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_container)

        # plot
        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)

        self.fig = Figure(figsize=(7, 3))
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

        plot_layout.addWidget(self.canvas)
        splitter.addWidget(plot_container)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

    # =============== LOGIC SCAN ===============

    def _run_scan(self):
        """Lọc theo số tháng gần nhất và chạy Mann–Kendall cho semua feature numeric."""
        months_back = self.spin_months.value()

        max_dt = self._orig_df[self.time_col].max()
        if pd.isna(max_dt):
            QMessageBox.warning(self, "Trend (Mann–Kendall)", "Không có dữ liệu thời gian hợp lệ.")
            return

        min_dt = max_dt - pd.DateOffset(months=months_back)
        df_win = self._orig_df[self._orig_df[self.time_col].between(min_dt, max_dt)].copy()

        if df_win.empty:
            self._current_window_df = df_win
            self.table.setRowCount(0)
            self.cb_feature.clear()
            self.ax.clear()
            self.ax.text(0.5, 0.5, "Không có dữ liệu trong khoảng thời gian này.",
                         ha="center", va="center")
            self.canvas.draw()
            return

        self._current_window_df = df_win

        # chọn cột numeric
        numeric_cols = df_win.select_dtypes(include=[np.number]).columns.tolist()
        # loại bỏ cột không muốn (nếu có)
        for col_drop in [self.time_col]:
            if col_drop in numeric_cols:
                numeric_cols.remove(col_drop)

        records = []
        self._feature_names = []

        for col in numeric_cols:
            series = df_win[[self.time_col, col]].dropna().sort_values(self.time_col)
            if len(series) < 10:
                # quá ít điểm, bỏ qua cho đỡ nhiễu
                continue

            x = series[col].to_numpy()

            try:
                result = mk.original_test(x)
                trend_raw = result.trend        # 'increasing', 'decreasing', 'no trend'
                tau = float(result.Tau)
                p_value = float(result.p)
            except Exception:
                trend_raw = "no trend"
                tau = np.nan
                p_value = np.nan

            trend_label, level_label = self._classify_trend(trend_raw, tau, p_value)

            records.append(
                (col, trend_label, level_label, tau, p_value, len(series))
            )
            self._feature_names.append(col)

        # cập nhật bảng
        self._fill_table(records)

        # cập nhật combobox feature
        self.cb_feature.blockSignals(True)
        self.cb_feature.clear()
        self.cb_feature.addItems(self._feature_names)
        self.cb_feature.blockSignals(False)

        if self._feature_names:
            self.cb_feature.setCurrentIndex(0)
            self._update_plot()
        else:
            self.ax.clear()
            self.ax.text(0.5, 0.5, "Không tìm thấy feature numeric phù hợp.",
                         ha="center", va="center")
            self.canvas.draw()

    def _classify_trend(self, trend_raw: str, tau: float, p_value: float):
        """
        Chuyển trend_raw + tau + p thành label tiếng Việt + mức độ.
        Mức độ: 2-Mạnh, 1-Vừa, 0-Yếu, 0-None.
        """
        if pd.isna(tau) or pd.isna(p_value):
            return "Không xác định", "0-None"

        # Chỉ coi là có trend nếu p < 0.05
        if p_value >= 0.05 or trend_raw == "no trend":
            return "Không rõ xu hướng", "0-None"

        direction = "Tăng" if trend_raw == "increasing" else "Giảm"
        at = abs(tau)

        if at >= 0.6:
            level = "2-Mạnh"
        elif at >= 0.3:
            level = "1-Vừa"
        else:
            level = "0-Yếu"

        label = f"{direction} ({level.split('-')[1]})"
        return label, level

    def _fill_table(self, records: list[tuple]):
        self.table.setRowCount(len(records))

        for row, (feat, trend_label, level_label, tau, p_val, n_points) in enumerate(records):
            items = [
                QTableWidgetItem(str(feat)),
                QTableWidgetItem(str(trend_label)),
                QTableWidgetItem(str(level_label)),
                QTableWidgetItem("" if pd.isna(tau) else f"{tau:.3f}"),
                QTableWidgetItem("" if pd.isna(p_val) else f"{p_val:.4f}"),
                QTableWidgetItem(str(n_points)),
            ]

            for col_idx, item in enumerate(items):
                # canh giữa cho đẹp
                if col_idx > 0:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col_idx, item)

            # Tô màu nhẹ cho xu hướng
            trend_str = trend_label or ""
            if trend_str.startswith("Tăng"):
                color = Qt.green
            elif trend_str.startswith("Giảm"):
                color = Qt.red
            else:
                color = None

            if color is not None:
                for col_idx in range(self.table.columnCount()):
                    it = self.table.item(row, col_idx)
                    if it is not None:
                        it.setBackground(color)

        self.table.resizeColumnsToContents()

    # =============== TƯƠNG TÁC UI ===============

    def _on_table_clicked(self, row: int, column: int):
        item = self.table.item(row, 0)
        if item is None:
            return
        feat = item.text()
        idx = self.cb_feature.findText(feat)
        if idx >= 0:
            self.cb_feature.setCurrentIndex(idx)

    def _update_plot(self):
        feat = self.cb_feature.currentText()
        if not feat:
            self.ax.clear()
            self.ax.text(0.5, 0.5, "Chưa chọn biến.",
                         ha="center", va="center")
            self.canvas.draw()
            return

        df = self._current_window_df
        if df.empty or feat not in df.columns:
            self.ax.clear()
            self.ax.text(0.5, 0.5, "Không có dữ liệu để vẽ.",
                         ha="center", va="center")
            self.canvas.draw()
            return

        series = df[[self.time_col, feat]].dropna().sort_values(self.time_col)
        if series.empty:
            self.ax.clear()
            self.ax.text(0.5, 0.5, "Không có dữ liệu hợp lệ cho biến này.",
                         ha="center", va="center")
            self.canvas.draw()
            return

        t = series[self.time_col].to_numpy()
        y = series[feat].to_numpy()

        self.fig.clear()
        self.ax = self.fig.add_subplot(111)

        # đường dữ liệu
        # self.ax.plot(t, y, marker="o", linestyle="-", label="Giá trị")

        # đường fit tuyến tính cho trực giác xu hướng
        # try:
        #     x_idx = np.arange(len(y), dtype=float)
        #     coef = np.polyfit(x_idx, y, deg=1)  # y ≈ a*x + b
        #     y_fit = np.polyval(coef, x_idx)
        #     self.ax.plot(t, y_fit,'b-', linestyle="--", label="Đường trend (linear fit)")
        # except Exception:
        #     pass
        # trendline theo Mann–Kendall (Theil–Sen slope/intercept) – chỉ vẽ trend
        try:
            if len(y) >= 2:
                x_idx = np.arange(len(y), dtype=float)

                # Lấy slope/intercept từ pymannkendall
                result = mk.original_test(y)
                slope = float(result.slope)
                intercept = float(result.intercept)

                y_fit = intercept + slope * x_idx

                # Chỉ vẽ trendline (không vẽ y thật)
                self.ax.plot(t, y_fit, linestyle="--", label="Trend (MK slope)")
        except Exception:
            pass


        self.ax.set_title(f"Trend của {feat} trong {self.spin_months.value()} tháng gần nhất")
        self.ax.set_xlabel("Thời gian")
        self.ax.set_ylabel(feat)
        self.ax.legend()
        self.fig.autofmt_xdate()

        self.canvas.draw()
