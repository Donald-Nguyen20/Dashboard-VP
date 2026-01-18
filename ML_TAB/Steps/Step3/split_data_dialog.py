# ML_TAB/Steps/Step3/split_data_dialog.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from sklearn.model_selection import train_test_split


@dataclass
class SplitResult:
    train_idx: np.ndarray
    test_idx: np.ndarray
    test_size: float
    random_state: int


class SplitDataDialog(QDialog):
    """
    Split theo ROW INDEX một lần cho toàn bộ DataFrame.
    Không chọn target ở Step 3.
    Step 5 sẽ chọn target sau và tự tạo X = các biến còn lại.
    """
    def __init__(self, df: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Split data (Train/Test)")
        self._df = df.copy()
        self.result: Optional[SplitResult] = None
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Test size (0-1):"))
        self.inp_test = QLineEdit("0.2")
        self.inp_test.setMaximumWidth(90)
        r2.addWidget(self.inp_test)
        r2.addStretch(1)
        lay.addLayout(r2)

        r3 = QHBoxLayout()
        r3.addWidget(QLabel("Random state:"))
        self.inp_seed = QLineEdit("42")
        self.inp_seed.setMaximumWidth(90)
        r3.addWidget(self.inp_seed)
        r3.addStretch(1)
        lay.addLayout(r3)

        btn_row = QHBoxLayout()
        self.btn_ok = QPushButton("Split")
        self.btn_cancel = QPushButton("Cancel")
        btn_row.addWidget(self.btn_ok)
        btn_row.addWidget(self.btn_cancel)
        lay.addLayout(btn_row)

        self.btn_ok.clicked.connect(self._do_split)
        self.btn_cancel.clicked.connect(self.reject)

    def _do_split(self):
        if self._df is None or self._df.empty:
            QMessageBox.warning(self, "No data", "DataFrame rỗng.")
            return

        try:
            test_size = float(self.inp_test.text().strip())
            seed = int(self.inp_seed.text().strip())
            if not (0.01 <= test_size <= 0.99):
                raise ValueError
        except Exception:
            QMessageBox.warning(self, "Invalid input", "Test size 0.01–0.99, random state là số nguyên.")
            return

        idx = self._df.index.to_numpy()
        if len(idx) < 20:
            QMessageBox.warning(self, "Too few rows", f"Dữ liệu quá ít ({len(idx)} dòng). Nên >= 20.")
            return

        idx_train, idx_test = train_test_split(
            idx, test_size=test_size, random_state=seed, shuffle=True
        )

        self.result = SplitResult(
            train_idx=idx_train,
            test_idx=idx_test,
            test_size=test_size,
            random_state=seed
        )
        self.accept()
