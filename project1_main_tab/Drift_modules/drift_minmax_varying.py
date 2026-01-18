# file: project1_main_tab/drift_minmax_varying.py

from __future__ import annotations

from typing import List, Dict, Optional

import pandas as pd
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QScrollArea,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QSizePolicy,
)

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from PySide6.QtCore import Qt
import mplcursors
from PySide6.QtGui import QColor


class MinMaxVaryingDialog(QDialog):
    """
    Drift view: Min/Max varying theo tháng.

    - Hàng dọc: tên feature
    - Cột ngang: 1..6 tháng trước (nếu đủ dữ liệu)
    - Ô = "Δmin% / Δmax%" so với tháng hiện tại
    - Có combo chọn feature + line chart min/max theo tháng
    """

    def __init__(self, df: pd.DataFrame, parent=None, months_back: int = 6):
        super().__init__(parent)
        self.setWindowTitle("Min/Max varying by month")
        self.resize(1000, 700)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)

        self.df = df.copy()
        self.months_back = months_back

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # ==== Chuẩn hóa Datetime & group theo tháng ====
        if "Datetime" not in self.df.columns:
            raise ValueError("DataFrame phải có cột 'Datetime' để tính Min/Max theo tháng.")

        self.df["Datetime"] = pd.to_datetime(self.df["Datetime"], errors="coerce")
        self.df = self.df.dropna(subset=["Datetime"]).sort_values("Datetime")

        # Chỉ lấy các cột numeric làm feature
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        self.feature_names: List[str] = [c for c in numeric_cols if c != "Datetime"]

        if not self.feature_names:
            raise ValueError("Không tìm thấy cột numeric nào để tính Min/Max.")

        # Tạo cột Month (period theo tháng)
        self.df["Month"] = self.df["Datetime"].dt.to_period("M")

        # monthly_min[feature][month] & monthly_max[feature][month]
        self.monthly_min: Dict[str, pd.Series] = {}
        self.monthly_max: Dict[str, pd.Series] = {}

        for col in self.feature_names:
            grp = self.df.groupby("Month")[col]
            self.monthly_min[col] = grp.min().sort_index()
            self.monthly_max[col] = grp.max().sort_index()

        # Lấy list tháng (Period M) & xác định tháng hiện tại + các tháng back
        all_months = sorted(self.df["Month"].unique())
        if len(all_months) < 2:
            raise ValueError("Không đủ >= 2 tháng dữ liệu để so sánh.")

        self.current_month = all_months[-1]
        # Lấy tối đa months_back tháng trước
        prev_months = all_months[:-1][-self.months_back :]
        # Đảo lại để 1M ago gần nhất → … → 6M ago xa nhất
        self.prev_months = list(reversed(prev_months))  # type: List[pd.Period]

        # ==== Header trên: giải thích + chọn feature để xem line chart ====
        header_layout = QHBoxLayout()
        lbl_title = QLabel(
            "Min/Max varying theo tháng hiện tại so với 1–6 tháng trước "
            f"(tháng hiện tại: {self.current_month})"
        )
        lbl_title.setWordWrap(True)

        header_layout.addWidget(lbl_title, 1)

        header_layout.addSpacing(12)


        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # ==== Khu vực scroll (bảng + plot) ====
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        # === Bảng Min/Max varying ===
        self.table = QTableWidget()
        self.build_minmax_table()
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- Click vào dòng / tên biến để đổi plot ---
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        # click vào bất kỳ ô nào trong dòng -> đổi plot
        self.table.cellClicked.connect(self._on_table_cell_clicked)

        # click đúng tên biến ở header trái -> đổi plot
        vh = self.table.verticalHeader()
        vh.setSectionsClickable(True)
        vh.sectionClicked.connect(self._on_vertical_header_clicked)


        scroll_layout.addWidget(QLabel("Bảng Δmin% / Δmax% so với tháng hiện tại"))
        scroll_layout.addWidget(self.table)

        # === Plot min/max theo tháng cho 1 feature ===
        self.fig = Figure(figsize=(6, 3))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar = NavigationToolbar(self.canvas, self)



        scroll_layout.addWidget(self.canvas)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Vẽ plot lần đầu (mặc định dòng 0)
        self.current_feature = self.feature_names[0]
        self.table.selectRow(0)
        self.update_plot(self.current_feature)


    # -------------------------------------------------
    def build_minmax_table(self):
        """
        Bảng Min/Max varying:

        - Cột 1..n: Δmin% / Δmax% so với tháng hiện tại.
        - Khối cảnh báo MAX:
            Shock Max 1M (>20%), Trend Max 2M..nM (so giữa các tháng kề nhau).
        - Khối cảnh báo MIN:
            Shock Min 1M (>20%), Trend Min 2M..nM (so giữa các tháng kề nhau).

        Trend kM:
            - Lấy k tháng gần nhất (k tháng cuối) theo thời gian.
            - Nếu tất cả các bước giữa tháng kề nhau cùng tăng → ↑xk (nền xanh).
            - Nếu tất cả cùng giảm → ↓xk (nền đỏ).
            - Chỉ xét max riêng, min riêng (không gộp).
        """
        n_feat = len(self.feature_names)
        base_cols = len(self.prev_months)   # số cột "1M ago, 2M ago, ..."
        if base_cols == 0:
            return

        # ----- Số cột: -----
        #   + base_cols cột Δ% (1M..nM)
        #   + base_cols cột cảnh báo MAX  (Shock + Trend 2..n)
        #   + base_cols cột cảnh báo MIN  (Shock + Trend 2..n)
        extra_cols = base_cols * 2
        total_cols = base_cols + extra_cols

        self.table.clear()
        self.table.setRowCount(n_feat)
        self.table.setColumnCount(total_cols)

        # ----- Header cột Δ% -----
        delta_headers = []
        for idx, m in enumerate(self.prev_months, start=1):
            delta_headers.append(f"{idx}M ago\n({str(m)})")

        # ----- Header cảnh báo MAX + MIN -----
        alert_max_headers = ["Fluctuation Max 1M (>20%)"]
        for k in range(2, base_cols + 1):
            alert_max_headers.append(f"Trend Max {k}M")

        alert_min_headers = ["Fluctuation Min 1M (>20%)"]
        for k in range(2, base_cols + 1):
            alert_min_headers.append(f"Trend Min {k}M")

        self.table.setHorizontalHeaderLabels(
            delta_headers + alert_max_headers + alert_min_headers
        )
        self.table.setVerticalHeaderLabels(self.feature_names)

        # ===== Điền dữ liệu từng feature =====
        for row, feat in enumerate(self.feature_names):
            s_min = self.monthly_min[feat]
            s_max = self.monthly_max[feat]

            if self.current_month not in s_min.index or self.current_month not in s_max.index:
                # Thiếu data tháng hiện tại → N/A toàn dòng
                for col_idx in range(total_cols):
                    self.table.setItem(row, col_idx, QTableWidgetItem("N/A"))
                continue

            cur_min = s_min.get(self.current_month, np.nan)
            cur_max = s_max.get(self.current_month, np.nan)

            # Lưu Δ% so với current cho từng tháng (dùng cho cột Shock)
            deltas_min: list[Optional[float]] = []
            deltas_max: list[Optional[float]] = []

            # ----- 1) Cột Δmin% / Δmax% so với tháng hiện tại -----
            for col_idx, m in enumerate(self.prev_months):
                old_min = s_min.get(m, np.nan)
                old_max = s_max.get(m, np.nan)

                if (
                    np.isnan(cur_min) or np.isnan(cur_max) or
                    np.isnan(old_min) or np.isnan(old_max) or
                    old_min == 0 or old_max == 0
                ):
                    text = "N/A"
                    dmin = dmax = None
                else:
                    dmin = (cur_min - old_min) / old_min * 100.0
                    dmax = (cur_max - old_max) / old_max * 100.0
                    text = f"{dmin:+.1f}% / {dmax:+.1f}%"

                deltas_min.append(dmin)
                deltas_max.append(dmax)

                item = QTableWidgetItem(text)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row, col_idx, item)

            # ===== Chuẩn bị list tháng theo thứ tự thời gian =====
            # prev_months đang là [1M ago, 2M ago, ..., nM ago] (tính từ hiện tại),
            # nên đảo ngược lại rồi cộng thêm current để có chuỗi tăng dần theo thời gian.
            months_chrono = list(reversed(self.prev_months)) + [self.current_month]
            max_k = min(base_cols + 1, len(months_chrono))

            def sign_diff(a, b) -> int:
                """Dấu của (b - a) theo giá trị tuyệt đối, 0 nếu không rõ."""
                if np.isnan(a) or np.isnan(b):
                    return 0
                diff = b - a
                if diff > 0:
                    return 1
                elif diff < 0:
                    return -1
                return 0

            # ===== 2) Khối cảnh báo MAX =====
            base_max_col = base_cols  # cột bắt đầu block MAX

            # Shock Max 1M: cột đầu tiên khối MAX
            shock_max_item = QTableWidgetItem("")
            shock_max_item.setFlags(shock_max_item.flags() ^ Qt.ItemIsEditable)
            if deltas_max and deltas_max[0] is not None:
                if abs(deltas_max[0]) > 20.0:
                    shock_max_item.setText("⚠")
                    shock_max_item.setBackground(QColor(255, 230, 180))  # cam nhạt
            self.table.setItem(row, base_max_col, shock_max_item)

            # Trend Max kM, k = 2..base_cols
            for k in range(2, max_k + 1):
                col_alert_idx = base_max_col + (k - 1)
                alert_text = ""
                bg_color = None

                # Lấy k tháng gần nhất (k tháng cuối) theo thời gian
                segment_months = months_chrono[-k:]

                signs: list[int] = []
                for i in range(1, len(segment_months)):
                    m_old = segment_months[i - 1]
                    m_new = segment_months[i]
                    old_val = s_max.get(m_old, np.nan)
                    new_val = s_max.get(m_new, np.nan)
                    s = sign_diff(old_val, new_val)
                    if s == 0:
                        signs = []
                        break
                    signs.append(s)

                if len(signs) == k - 1:
                    if all(s == 1 for s in signs):
                        alert_text = f"↑x{k}"
                        bg_color = QColor(200, 255, 200)  # xanh nhạt
                    elif all(s == -1 for s in signs):
                        alert_text = f"↓x{k}"
                        bg_color = QColor(255, 200, 200)  # đỏ nhạt

                item_alert = QTableWidgetItem(alert_text)
                item_alert.setFlags(item_alert.flags() ^ Qt.ItemIsEditable)
                if bg_color is not None:
                    item_alert.setBackground(bg_color)
                self.table.setItem(row, col_alert_idx, item_alert)

            # ===== 3) Khối cảnh báo MIN =====
            base_min_col = base_cols + base_cols  # block MIN bắt đầu sau block MAX

            # Shock Min 1M
            shock_min_item = QTableWidgetItem("")
            shock_min_item.setFlags(shock_min_item.flags() ^ Qt.ItemIsEditable)
            if deltas_min and deltas_min[0] is not None:
                if abs(deltas_min[0]) > 20.0:
                    shock_min_item.setText("⚠")
                    shock_min_item.setBackground(QColor(255, 230, 180))
            self.table.setItem(row, base_min_col, shock_min_item)

            # Trend Min kM, k = 2..base_cols
            for k in range(2, max_k + 1):
                col_alert_idx = base_min_col + (k - 1)
                alert_text = ""
                bg_color = None

                segment_months = months_chrono[-k:]

                signs: list[int] = []
                for i in range(1, len(segment_months)):
                    m_old = segment_months[i - 1]
                    m_new = segment_months[i]
                    old_val = s_min.get(m_old, np.nan)
                    new_val = s_min.get(m_new, np.nan)
                    s = sign_diff(old_val, new_val)
                    if s == 0:
                        signs = []
                        break
                    signs.append(s)

                if len(signs) == k - 1:
                    if all(s == 1 for s in signs):
                        alert_text = f"↑x{k}"
                        bg_color = QColor(200, 255, 200)
                    elif all(s == -1 for s in signs):
                        alert_text = f"↓x{k}"
                        bg_color = QColor(255, 200, 200)

                item_alert = QTableWidgetItem(alert_text)
                item_alert.setFlags(item_alert.flags() ^ Qt.ItemIsEditable)
                if bg_color is not None:
                    item_alert.setBackground(bg_color)
                self.table.setItem(row, col_alert_idx, item_alert)

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def _select_feature(self, feat: str):
        """Chọn feature bằng click bảng -> vẽ plot ngay."""
        if feat not in self.feature_names:
            return
        self.current_feature = feat
        self.update_plot(feat)


    def _on_table_cell_clicked(self, row: int, col: int):
        """Click vào cell bất kỳ -> dùng row để suy ra feature."""
        if 0 <= row < len(self.feature_names):
            self._select_feature(self.feature_names[row])

    def _on_vertical_header_clicked(self, row: int):
        """Click vào tên biến (vertical header) -> chọn row + đổi plot."""
        if 0 <= row < len(self.feature_names):
            self.table.selectRow(row)
            self._select_feature(self.feature_names[row])


    # -------------------------------------------------
    def update_plot(self, feature_name: str):
        """
        Vẽ line min/max theo tháng (có cả tháng hiện tại và các tháng trước),
        kèm tooltip khi hover vào từng điểm.
        """
        if feature_name not in self.feature_names:
            return

        s_min = self.monthly_min[feature_name]
        s_max = self.monthly_max[feature_name]

        # Lấy list tháng để vẽ: prev_months (đảo lại cho tăng dần) + current
        months_for_plot = list(reversed(self.prev_months)) + [self.current_month]
        x_labels = [str(m) for m in months_for_plot]

        # Dữ liệu min/max cho từng tháng
        y_min = [s_min.get(m, np.nan) for m in months_for_plot]
        y_max = [s_max.get(m, np.nan) for m in months_for_plot]

        # Dùng chỉ số 0,1,2,... làm trục X cho dễ quản lý tooltip
        x_idx = np.arange(len(months_for_plot))

        self.fig.clear()
        ax = self.fig.add_subplot(111)
        self.ax = ax  # nếu sau này anh muốn dùng giống plot_tab

        # Vẽ line và giữ reference
        line_min, = ax.plot(x_idx, y_min, marker="o", label="Min")
        line_max, = ax.plot(x_idx, y_max, marker="o", label="Max")

        ax.set_title(f"Min/Max theo tháng - {feature_name}")
        ax.set_xlabel("Month")
        ax.set_ylabel(feature_name)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # Gán nhãn tháng cho trục X
        ax.set_xticks(x_idx)
        ax.set_xticklabels(x_labels, rotation=45, ha="right")

        # ===== Tooltip với mplcursors =====
        cursor = mplcursors.cursor([line_min, line_max], hover=True)

        @cursor.connect("add")
        def on_add(sel):
            line = sel.artist
            # sel.index đôi khi là float → ép int cho chắc
            i = int(round(sel.index))

            if i < 0 or i >= len(x_labels):
                return

            month_label = x_labels[i]
            y_val = line.get_ydata()[i]
            series_name = line.get_label()  # "Min" hoặc "Max"

            sel.annotation.set(
                text=(
                    f"{series_name}\n"
                    f"Month: {month_label}\n"
                    f"{feature_name}: {y_val:.2f}"
                )
            )
            sel.annotation.get_bbox_patch().set(alpha=0.9)

        self.fig.tight_layout()
        self.canvas.draw()

