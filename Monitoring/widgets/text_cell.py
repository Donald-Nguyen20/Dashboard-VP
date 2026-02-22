"""
Widget ô nhập text đánh giá.
"""
from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import QFrame, QVBoxLayout, QTextEdit, QLabel
from PySide6.QtCore import Qt
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu

class TextCellWidget(QFrame):
    """Ô nhập text đánh giá / ghi chú."""
    def __init__(self, initial_text: str = "", parent: Optional[QFrame] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.setStyleSheet("""
            TextCellWidget {
                background: #fafbfc;
                border: 1px solid #d0d7de;
                border-radius: 8px;
            }
        """)
        self.setMinimumSize(200, 120)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Nhập đánh giá / ghi chú...")
        self.text_edit.setPlainText(initial_text)
        layout.addWidget(self.text_edit)

    def get_content(self) -> str:
        return self.text_edit.toPlainText()

    def set_content(self, text: str) -> None:
        self.text_edit.setPlainText(text or "")

    def _show_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        act_clear = menu.addAction("🗑️ Clear")
        action = menu.exec(self.mapToGlobal(pos))
        if action == act_clear and hasattr(self, "on_clear"):
            self.on_clear()
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        act_clear = menu.addAction("🧹 Clear / Remove this cell")
        action = menu.exec(event.globalPos())
        if action == act_clear:
            if hasattr(self, "on_clear") and callable(self.on_clear):
                self.on_clear()