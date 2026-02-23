"""
Ô nhúng đồ thị Plotly — load từ file HTML giống hệt tab Plotly (QWebEngineView.load file), không kaleido.
"""
from __future__ import annotations
import tempfile
from typing import Optional
from PySide6.QtWidgets import QFrame, QVBoxLayout, QMenu
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView


class PlotlyEmbedCell(QFrame):
    """Ô hiển thị đồ thị Plotly: load từ file (path hoặc ghi content ra file) — giống tab Plotly."""
    def __init__(self, html_content: str = "", html_path: str | None = None, parent: Optional[QFrame] = None):
        super().__init__(parent)
        self.html_content = html_content
        self.setFrameShape(QFrame.StyledPanel)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.setStyleSheet("""
            PlotlyEmbedCell {
                background: #fafbfc;
                border: 1px solid #d0d7de;
                border-radius: 8px;
            }
        """)
        self.setMinimumSize(280, 200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self.web_view = QWebEngineView()
        self.web_view.setMinimumSize(260, 180)
        layout.addWidget(self.web_view)
        if html_path:
            try:
                self.web_view.load(QUrl.fromLocalFile(html_path))
            except Exception:
                if html_content:
                    self._load_content(html_content)
        elif html_content:
            self._load_content(html_content)

    def _load_content(self, html: str) -> None:
        """Ghi HTML ra file rồi load — giống tab Plotly."""
        if not html:
            return
        try:
            f = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".html")
            f.write(html)
            f.close()
            self.web_view.load(QUrl.fromLocalFile(f.name))
        except Exception:
            pass

    def set_html_content(self, html: str) -> None:
        self.html_content = html
        self._load_content(html)

    def _show_menu(self, pos):
        menu = QMenu(self)
        act_refresh = menu.addAction("🔄 Lấy lại đồ thị")
        act_clear = menu.addAction("🗑️ Xóa")
        action = menu.exec(self.mapToGlobal(pos))
        if action == act_refresh and hasattr(self, "on_refresh"):
            self.on_refresh()
        elif action == act_clear and hasattr(self, "on_clear"):
            self.on_clear()
