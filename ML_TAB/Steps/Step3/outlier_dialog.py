# ML_TAB/Steps/Step3/outlier_dialog.py
from __future__ import annotations

from typing import Optional, List

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QComboBox,
)
from PySide6.QtCore import Qt

class OutlierResultsDialog(QDialog):
    """
    Dialog hiển thị kết quả phát hiện outlier ở nhiều tab (IQR + Z-Score, IQR, Z-Score,
    IsolationForest, LOF...).

    - Mỗi tab là một QTableWidget.
    - Cột 'row_index' có checkbox để chọn những dòng muốn xoá.
    - Khi bấm 'Delete selected rows', dialog sẽ:
        + Gom tất cả row_index được tick ở mọi tab
        + Lưu vào self.rows_to_delete (list[int])
        + Trả về Accepted.
    - Nếu bấm 'Close' thì trả về Rejected và không xoá gì.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OutlierDialog")
        self.setWindowTitle("Outlier Detection — Results")
        self.resize(1000, 620)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.WindowSystemMenuHint)
        # ========== THEME XANH CHO DIALOG + BẢNG ==========
        self.setStyleSheet("""
        /* NỀN & KHUNG DIALOG */
        #OutlierDialog {
            background-color: #eaf3ff;            /* xanh dương rất nhạt */
        }

        /* NÚT (Delete) */
        #OutlierDialog QPushButton {
            background-color: #a9c7ff;
            color: #111;
            border: 1px solid #7ea9ff;
            border-radius: 6px;
            padding: 4px 12px;
        }
        #OutlierDialog QPushButton:hover {
            background-color: #7ea9ff;
        }

        /* TAB BAR PHƯƠNG PHÁP OUTLIER */
        #OutlierDialog QTabWidget::pane {
            background: transparent;
            border: none;
        }

        #OutlierDialog QTabBar::tab {
            background-color: #a9c7ff;
            color: #111;
            padding: 6px 14px;
            border-radius: 8px 8px 0 0;
            margin-right: 4px;
            min-width: 90px;
        }
        #OutlierDialog QTabBar::tab:selected {
            background-color: #7ea9ff;
            font-weight: 600;
        }
        #OutlierDialog QTabBar::tab:hover {
            background-color: #8fb8ff;
        }

        /* BẢNG KẾT QUẢ – XANH MINT */
        #OutlierDialog QTableWidget {
            background-color: #e6fff5;            /* nền mint nhạt */
            alternate-background-color: #f4fffb;  /* hàng xen kẽ sáng hơn */
            color: #111;
            gridline-color: #7fe8c4;              /* kẻ ô xanh mint đậm */
            border: 1px solid #7fe8c4;
            selection-background-color: #a5f3fc;  /* chọn hàng: xanh cyan nhạt */
            selection-color: #111;
        }

        #OutlierDialog QHeaderView::section {
            background-color: #7fe8c4;            /* header xanh mint đậm hơn */
            color: #111;
            padding: 4px 6px;
            border: 0;
            border-right: 1px solid #e6fff5;
            font-weight: 600;
        }
        """)

        # Danh sách row_index được tick để xoá
        self.rows_to_delete: List[int] = []

        outer = QVBoxLayout(self)

               # ===== HEADER =====
        header = QHBoxLayout()

        header.addStretch(1)

        self.btnDelete = QPushButton("Delete selected rows")
        self.btnDelete.clicked.connect(self._on_delete_selected)
        header.addWidget(self.btnDelete, 0, Qt.AlignRight)

        outer.addLayout(header)


        # ===== TAB WIDGET =====
        self.tabs = QTabWidget(self)

        # tắt mũi tên scroll để hiện đủ tab
        tabbar = self.tabs.tabBar()
        tabbar.setUsesScrollButtons(False)
        tabbar.setExpanding(False)

        outer.addWidget(self.tabs, 1)
        # Không còn layout bottom, nút Delete đã được đưa lên header





    # ------------------------------------------------------------------
    # Thêm một tab kết quả
    # ------------------------------------------------------------------
    def add_tab(self, name: str, df: Optional[pd.DataFrame]):
        """
        Thêm một tab với tên 'name' và dữ liệu 'df'.
        df mong đợi có ít nhất các cột:
            row_index | timestamp | column | value | score | method
        Nếu có thêm cột 'causes' sẽ hiển thị thêm ở cuối.
        """
        widget = QWidget(self)
        layout = QVBoxLayout(widget)

        base_headers = ["row_index", "timestamp", "column", "value", "score", "method"]
        headers = base_headers.copy()

        # nếu DF có cột 'causes' thì thêm vào
        if df is not None and ("causes" in df.columns):
            headers.append("causes")

        table = QTableWidget(widget)
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)

        if df is not None and not df.empty:
            table.setRowCount(len(df))

            for r, (_, row) in enumerate(df.iterrows()):
                # --- row_index (checkable) ---
                ridx = row.get("row_index", "")
                idx_item = QTableWidgetItem(str(ridx))
                idx_item.setTextAlignment(Qt.AlignCenter)
                idx_item.setFlags(idx_item.flags() | Qt.ItemIsUserCheckable)
                idx_item.setCheckState(Qt.Unchecked)
                table.setItem(r, 0, idx_item)

                # --- timestamp ---
                ts = str(row.get("timestamp", ""))
                table.setItem(r, 1, QTableWidgetItem(ts))

                # --- column ---
                col_name = str(row.get("column", ""))
                table.setItem(r, 2, QTableWidgetItem(col_name))

                # --- value ---
                val = row.get("value", "")
                if isinstance(val, (int, float)) and not pd.isna(val):
                    txt_val = f"{val:.6g}"
                else:
                    txt_val = "" if pd.isna(val) else str(val)
                table.setItem(r, 3, QTableWidgetItem(txt_val))

                # --- score ---
                score = row.get("score", "")
                if isinstance(score, (int, float)) and not pd.isna(score):
                    txt_score = f"{score:.6f}"
                else:
                    txt_score = "" if pd.isna(score) else str(score)
                score_item = QTableWidgetItem(txt_score)
                score_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(r, 4, score_item)

                # --- method ---
                method = str(row.get("method", ""))
                table.setItem(r, 5, QTableWidgetItem(method))

                # --- causes (nếu có) ---
                if "causes" in headers:
                    cidx = headers.index("causes")
                    causes_str = str(row.get("causes", ""))
                    table.setItem(r, cidx, QTableWidgetItem(causes_str))

            table.resizeColumnsToContents()
        else:
            table.setRowCount(0)

        layout.addWidget(table)
        self.tabs.addTab(widget, name)

    # ------------------------------------------------------------------
    # Gom row_index đã tick ở mọi tab khi bấm Delete selected rows
    # ------------------------------------------------------------------
    def _on_delete_selected(self):
        rows = set()

        for t_idx in range(self.tabs.count()):
            page = self.tabs.widget(t_idx)
            if not page:
                continue

            table = page.findChild(QTableWidget)
            if table is None:
                continue

            # cột 0 = row_index (checkable)
            for r in range(table.rowCount()):
                item = table.item(r, 0)
                if not item:
                    continue
                if item.checkState() == Qt.Checked:
                    try:
                        ridx = int(item.text())
                        rows.add(ridx)
                    except ValueError:
                        pass

        if not rows:
            QMessageBox.information(self, "No selection", "Chưa tick dòng nào để xoá.")
            return

        self.rows_to_delete = sorted(rows)
        self.accept()
