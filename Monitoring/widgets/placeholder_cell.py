"""
Ô placeholder - hiển thị khi ô trống, right-click để chọn Get Plot hoặc Note.
"""
from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal


class PlaceholderCell(QFrame):
    """Ô trống có thể right-click: Get Plot | Note."""
    get_plot_requested = Signal(int, int)  # row, col
    note_requested = Signal(int, int)
    selected = Signal(int, int)  # row, col (để chọn hàng đang thao tác)

    def __init__(self, row: int, col: int, parent: Optional[QFrame] = None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            PlaceholderCell {
                background: #f0f4f8;
                border: 2px dashed #b6c7d8;
                border-radius: 8px;
            }
            PlaceholderCell:hover {
                background: #e8eef4;
                border-color: #97b3d0;
            }
        """)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setMinimumSize(200, 120)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        lbl = QLabel(f"R{row+1} × C{col+1}")
        lbl.setStyleSheet("color: #6c757d; font-size: 12px;")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        hint = QLabel("Chuột phải → Get Plot / Note")
        hint.setStyleSheet("color: #adb5bd; font-size: 10px;")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def _show_context_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        act_get = menu.addAction("📈 Get Plot")
        act_note = menu.addAction("📝 Note")
        action = menu.exec(self.mapToGlobal(pos))
        if action == act_get:
            self.get_plot_requested.emit(self.row, self.col)
        elif action == act_note:
            self.note_requested.emit(self.row, self.col)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.row, self.col)
        super().mousePressEvent(event)