from __future__ import annotations
from typing import List, Optional
import pandas as pd

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser, QPushButton, QSizePolicy
)

from Monitoring.operating_report.report_builder import build_operating_report


class OperatingReportPanel(QFrame):
    """
    Panel báo cáo có thể Collapse/Expand.
    - Nút ▾/▸ để thu gọn/mở rộng
    - Nút ⤢ để maximize/restore (tăng/giảm chiều cao)
    """
    def __init__(self, parent=None, collapsed: bool = False):
        super().__init__(parent)
        self.setObjectName("OperatingReportPanel")

        self._collapsed = bool(collapsed)
        self._maximized = False
        self._normal_min_h = 240
        self._max_min_h = 720

        # ---------- Header ----------
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        self.btn_toggle = QPushButton("▾")   # collapse/expand
        self.btn_toggle.setFixedWidth(34)
        self.btn_toggle.clicked.connect(self.toggle_collapsed)

        self.title = QLabel("Operating Report")
        self.title.setStyleSheet("font-weight:700;")

        self.btn_max = QPushButton("⤢")      # maximize/restore height
        self.btn_max.setFixedWidth(34)
        self.btn_max.clicked.connect(self.toggle_maximized)

        header.addWidget(self.btn_toggle)
        header.addWidget(self.title, 1)
        header.addWidget(self.btn_max)

        # ---------- Body ----------
        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(False)
        self.viewer.setStyleSheet("padding:8px;")
        self.viewer.setMinimumHeight(self._normal_min_h)
        self.viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)

        # ---------- Root layout ----------
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self.viewer)

        self.setStyleSheet(
            """
            #OperatingReportPanel{
                border: 1px solid rgba(120,120,120,0.35);
                border-radius: 10px;
                background: rgba(255,255,255,0.75);
            }
            QPushButton{
                padding: 2px 6px;
                border-radius: 8px;
            }
            """
        )

        # Apply initial state
        if self._collapsed:
            self.set_collapsed(True)

    # -----------------------------
    # Public API
    # -----------------------------
    def clear(self):
        self.viewer.setHtml("")

    def update_report(
        self,
        df_range: pd.DataFrame,
        tags: List[str],
        time_col: Optional[str] = None,
        mw_col: Optional[str] = None,
    ):
        html = build_operating_report(df_range=df_range, tags=tags, time_col=time_col, mw_col=mw_col)
        self.viewer.setHtml(html)

    # -----------------------------
    # UI Actions
    # -----------------------------
    def toggle_collapsed(self):
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool):
        self._collapsed = bool(collapsed)

        if self._collapsed:
            self.btn_toggle.setText("▸")
            self.viewer.setVisible(False)
            # khi collapse: cũng reset maximize
            self._maximized = False
            self.btn_max.setText("⤢")
        else:
            self.btn_toggle.setText("▾")
            self.viewer.setVisible(True)
            # restore height theo trạng thái hiện tại
            self.viewer.setMinimumHeight(self._max_min_h if self._maximized else self._normal_min_h)

    def toggle_maximized(self):
        # nếu đang collapse thì mở ra trước
        if self._collapsed:
            self.set_collapsed(False)

        self._maximized = not self._maximized
        if self._maximized:
            self.btn_max.setText("⤡")  # restore icon
            self.viewer.setMinimumHeight(self._max_min_h)
        else:
            self.btn_max.setText("⤢")
            self.viewer.setMinimumHeight(self._normal_min_h)