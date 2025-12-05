# ML_TAB/Steps/Step2/dashboard_widget.py
from __future__ import annotations
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView


class ProfileDashboard(QWidget):
    """
    Dashboard hiển thị trực tiếp HTML report của ydata_profiling
    -> giống hệt giao diện HTML (CSS/JS/biểu đồ tương tác đầy đủ).
    """
    def __init__(self, html_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Step 2 — Data Profile (HTML)")
        self.resize(1100, 800)

        layout = QVBoxLayout(self)
        self.web = QWebEngineView(self)
        self.web.setUrl(QUrl.fromLocalFile(html_path))
        layout.addWidget(self.web)
