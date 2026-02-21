"""
Dialog thêm ô đồ thị - chọn loại chart và biến.
"""
from __future__ import annotations
from typing import Optional
import pandas as pd
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
    QPushButton,
    QMessageBox,
)


class AddChartDialog(QDialog):
    """Dialog thêm ô đồ thị - chọn chart type và variables."""
    def __init__(self, columns: list[str], parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setWindowTitle("Thêm đồ thị")
        self.columns = columns or []
        layout = QVBoxLayout(self)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Loại đồ thị:"))
        self.chart_combo = QComboBox()
        self.chart_combo.addItems(["Line", "Scatter", "Bar", "Histogram", "Boxplot"])
        row1.addWidget(self.chart_combo)
        layout.addLayout(row1)

        layout.addWidget(QLabel("Chọn biến (giữ Ctrl để chọn nhiều):"))
        self.var_list = QListWidget()
        self.var_list.setSelectionMode(QListWidget.ExtendedSelection)
        for col in self.columns:
            self.var_list.addItem(col)
        layout.addWidget(self.var_list)

        self.btn_select_all = QPushButton("Chọn tất cả")
        self.btn_select_all.clicked.connect(self._select_all)
        layout.addWidget(self.btn_select_all)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_ok)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _select_all(self):
        self.var_list.selectAll()

    def _on_ok(self):
        vars_selected = [i.text() for i in self.var_list.selectedItems()]
        chart = self.chart_combo.currentText().lower()
        if chart == "scatter" and len(vars_selected) != 2:
            QMessageBox.warning(self, "Lưu ý", "Scatter cần đúng 2 biến.")
            return
        if not vars_selected:
            QMessageBox.warning(self, "Lưu ý", "Chọn ít nhất 1 biến.")
            return
        self.accept()

    def get_config(self) -> dict:
        vars_selected = [i.text() for i in self.var_list.selectedItems()]
        return {
            "chart_type": self.chart_combo.currentText().lower(),
            "vars": vars_selected,
            "scales": {},
        }
