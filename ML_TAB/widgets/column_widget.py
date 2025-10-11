# widgets/column_widget.py
from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QSizePolicy, QSpacerItem, QLayout

class ColumnWidget(QFrame):
    """
    Cột dọc (V) KHÔNG tiêu đề — tự co theo kích thước StepCard bên trong.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("columnFrame")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # cho cột fit theo nội dung (StepCard)
        outer.setSizeConstraint(QLayout.SetFixedSize)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.content = QVBoxLayout()
        self.content.setSpacing(12)
        outer.addLayout(self.content)

        outer.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
