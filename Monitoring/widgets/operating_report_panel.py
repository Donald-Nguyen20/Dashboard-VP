from __future__ import annotations
from typing import List, Optional
import pandas as pd

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QTextBrowser

from Monitoring.operating_report.report_builder import build_operating_report


class OperatingReportPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OperatingReportPanel")

        self.title = QLabel("Operating Report")
        self.title.setStyleSheet("font-weight:700; padding:6px 2px;")

        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(False)
        self.viewer.setStyleSheet("padding:8px;")
        self.viewer.setMinimumHeight(700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(self.title)
        layout.addWidget(self.viewer)

        self.setStyleSheet(
            """
            #OperatingReportPanel{
                border: 1px solid rgba(120,120,120,0.35);
                border-radius: 10px;
                background: rgba(255,255,255,0.75);
            }
            """
        )

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