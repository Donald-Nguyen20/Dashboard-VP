from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy

class StepCard(QFrame):
    clicked = Signal(int)

    def __init__(self, step_no: int, title: str, subtitle: str = "", parent: Optional[QFrame] = None):
        super().__init__(parent)
        self.setObjectName("stepCard")      # ✅ trùng selector QSS
        self.setProperty("state", "idle")   # idle/busy/done/error (nếu cần)
        self.step_no = step_no
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        badge = QLabel(f"STEP {step_no}")
        badge.setObjectName("badge")
        layout.addWidget(badge)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("title")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setObjectName("subtitle")
            sub_lbl.setWordWrap(True)
            layout.addWidget(sub_lbl)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setFixedHeight(110)

    def set_state(self, state: str):
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.clicked.emit(self.step_no)
        return super().mouseReleaseEvent(ev)
