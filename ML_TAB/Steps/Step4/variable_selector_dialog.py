# file: ML_TAB/Steps/Step4/variable_selector_dialog.py

from __future__ import annotations

from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QScrollArea,
    QDialogButtonBox,
    QCheckBox,
    QPushButton,
)


class VariableSelectorDialog(QDialog):
    """
    Dialog chọn biến để vẽ (nhiều biến cùng lúc).
    """
    def __init__(self, columns: List[str], selected_vars: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn biến để vẽ")
        self.selected_vars = selected_vars or []
        self.checkboxes: List[QCheckBox] = []

        layout = QVBoxLayout(self)
        self.setMinimumSize(400, 500)

        # Widget chứa checkbox
        checkbox_widget = QWidget()
        checkbox_layout = QVBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(4, 4, 4, 4)
        checkbox_layout.setSpacing(2)

        for col in columns:
            cb = QCheckBox(col)
            # nếu chưa có selected_vars -> chọn hết mặc định
            cb.setChecked(col in self.selected_vars or not self.selected_vars)
            checkbox_layout.addWidget(cb)
            self.checkboxes.append(cb)
        checkbox_layout.addStretch()

        # Scroll cho danh sách dài
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(checkbox_widget)
        scroll.setMinimumHeight(200)
        scroll.setMaximumHeight(600)
        layout.addWidget(scroll)

        # Nút check all / uncheck all
        action_layout = QHBoxLayout()
        btn_check_all = QPushButton("✅ Chọn tất cả")
        btn_uncheck_all = QPushButton("❌ Bỏ chọn tất cả")
        btn_check_all.clicked.connect(self.check_all)
        btn_uncheck_all.clicked.connect(self.uncheck_all)
        action_layout.addWidget(btn_check_all)
        action_layout.addWidget(btn_uncheck_all)
        layout.addLayout(action_layout)

        # OK / Cancel
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_selected_variables(self) -> List[str]:
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

    def check_all(self):
        for cb in self.checkboxes:
            cb.setChecked(True)

    def uncheck_all(self):
        for cb in self.checkboxes:
            cb.setChecked(False)
