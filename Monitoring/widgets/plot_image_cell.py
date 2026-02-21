"""
Ô hiển thị đồ thị đã capture từ tab Plot (ảnh snapshot).
"""
from __future__ import annotations
import base64
from typing import Optional
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


class PlotImageCell(QFrame):
    """Ô hiển thị ảnh đồ thị (chụp từ Plot tab)."""
    def __init__(self, image_base64: str = "", parent: Optional[QFrame] = None):
        super().__init__(parent)
        self.image_base64 = image_base64
        self.setFrameShape(QFrame.StyledPanel)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.setStyleSheet("""
            PlotImageCell {
                background: #fafbfc;
                border: 1px solid #d0d7de;
                border-radius: 8px;
            }
        """)
        self.setMinimumSize(280, 200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setScaledContents(False)
        self.label.setMinimumSize(260, 180)
        layout.addWidget(self.label)
        if image_base64:
            self._set_image(image_base64)

    def _set_image(self, b64: str) -> None:
        try:
            data = base64.b64decode(b64)
            pix = QPixmap()
            if pix.loadFromData(data):
                scaled = pix.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.label.setPixmap(scaled)
        except Exception:
            self.label.setText("Lỗi hiển thị ảnh")

    def set_image_from_base64(self, b64: str) -> None:
        self.image_base64 = b64
        self._set_image(b64)

    def _show_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        act_refresh = menu.addAction("🔄 Re-capture")
        act_clear = menu.addAction("🗑️ Clear")
        action = menu.exec(self.mapToGlobal(pos))
        if action == act_refresh and hasattr(self, "on_refresh"):
            self.on_refresh()
        elif action == act_clear and hasattr(self, "on_clear"):
            self.on_clear()
