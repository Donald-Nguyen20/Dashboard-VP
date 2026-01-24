# ML_TAB/Steps/Step5/regression_algorithms_dialog.py
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QListWidget, QListWidgetItem, QStackedWidget, QWidget, QFrame,
    QMessageBox
)

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.metrics import mean_squared_error
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
import numpy as np
from sklearn.preprocessing import StandardScaler

class RegressionAlgorithmsDialog(QDialog):
    """
    UI:
    - Bên trái: list thuật toán (chỉ tên)
    - Bên phải: panel chi tiết (hiện khi click)
    """
    def __init__(self, parent_tab, parent=None):
        super().__init__(parent)
        self.parent_tab = parent_tab  # MLApplicationTab
        self.setWindowTitle("Step 5 - Regression Algorithms")
        self.resize(860, 520)

        root = QVBoxLayout(self)

        # ===== Header: chọn target =====
        header = QFrame(self)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(10, 10, 10, 10)

        h_lay.addWidget(QLabel("Target (y):"))
        self.cb_target = QComboBox()
        self.cb_target.addItems(self._get_numeric_targets())
        h_lay.addWidget(self.cb_target, 1)

        root.addWidget(header)

        # ===== Body: list (left) + details (right) =====
        body = QFrame(self)
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(10, 10, 10, 10)
        body_lay.setSpacing(12)
        root.addWidget(body, 1)

        # Left: algorithm names only
        self.list_algo = QListWidget()
        self.list_algo.setFixedWidth(240)
        body_lay.addWidget(self.list_algo)

        # Right: details panel
        self.stack = QStackedWidget()
        self._ui_refs = {}  # lưu label metrics + table theo key thuật toán
        body_lay.addWidget(self.stack, 1)

        # Add algorithms
        self._add_algorithm(
            key="LinearRegression",
            title="LinearRegression (sklearn)",

            train_fn=self._train_linear_regression
        )

        # default select first
        if self.list_algo.count() > 0:
            self.list_algo.setCurrentRow(0)
            self.stack.setCurrentIndex(0)

        self.list_algo.currentRowChanged.connect(self.stack.setCurrentIndex)

    def _get_numeric_targets(self):
        df = self.parent_tab._get_active_df_for_split()
        if df is None or df.empty:
            return []
        return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    def _add_algorithm(self, key: str, title: str, train_fn):
        # list item = name only
        item = QListWidgetItem(key)
        item.setData(Qt.UserRole, key)
        self.list_algo.addItem(item)

        # details widget
        w = QFrame()
        w.setObjectName(f"algoDetails_{key}")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-weight: 800; font-size: 15px;")
        lay.addWidget(lbl_title)

        # ✅ Metrics label (sẽ update sau khi train)
        lbl_metrics = QLabel("Metrics: (chưa train)")
        lbl_metrics.setStyleSheet("font-weight: 600;")
        lay.addWidget(lbl_metrics)

        btn_row = QHBoxLayout()
        btn_train = QPushButton(f"Train {key}")
        btn_train.clicked.connect(train_fn)
        btn_row.addWidget(btn_train)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        # ✅ Table Actual vs Prediction
        tbl = QTableWidget()
        tbl.setColumnCount(4)
        tbl.setHorizontalHeaderLabels(["Datetime", "Actual", "Prediction", "Error"])
        tbl.setRowCount(0)
        tbl.setMinimumHeight(260)
        lay.addWidget(tbl, 1)

        self._ui_refs[key] = {"metrics": lbl_metrics, "table": tbl}

        self.stack.addWidget(w)


    def _train_linear_regression(self):
        # 1) kiểm tra đã split chưa
        if not hasattr(self.parent_tab, "train_idx") or not hasattr(self.parent_tab, "test_idx"):
            QMessageBox.warning(self, "Chưa Split", "Hãy bấm Split data ở Step 3 trước.")
            return

        y_col = self.cb_target.currentText().strip()
        if not y_col:
            QMessageBox.warning(self, "Thiếu target", "Không có cột target numeric để train.")
            return

        # 2) build X/y theo target (X = các biến còn lại)
        try:
            x_cols, X_train, y_train, X_test, y_test = self.parent_tab.build_xy_for_target(y_col)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi build XY", str(e))
            return

        if len(y_train) < 20 or len(y_test) < 5:
            QMessageBox.warning(self, "Dữ liệu ít", f"Không đủ dữ liệu sau dropna. Train={len(y_train)}, Test={len(y_test)}")
            return
        # 3) scaler (fit on train, transform train + test)
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)   # fit + transform train
        X_test  = scaler.transform(X_test)        # transform test only

        # 3) train
        model = LinearRegression()
        model.fit(X_train, y_train)

        # 4) evaluate nhanh (TEST)
        pred_test = model.predict(X_test)
        mae = float(mean_absolute_error(y_test, pred_test))
        mse = float(mean_squared_error(y_test, pred_test))
        r2 = float(r2_score(y_test, pred_test))

        # ✅ tạo bảng actual/pred/error (lấy tối đa 200 dòng để mượt UI)
        n_show = min(200, len(y_test))
        y_true_show = y_test[:n_show]
        y_pred_show = pred_test[:n_show]
        err_show = y_true_show - y_pred_show

        # lấy Datetime nếu có (ưu tiên đúng các row test sau dropna)
        dt_col = None
        df_active = self.parent_tab._get_active_df_for_split()
        if df_active is not None and "Datetime" in df_active.columns:
            dt_col = "Datetime"

        # vì build_xy_for_target đã dropna, ta không còn index ở đây,
        # nên dùng Datetime = "" nếu không lấy được (để UI không lỗi).
        # (nâng cấp sau: trả thêm index từ build_xy_for_target để map Datetime chuẩn tuyệt đối)
        dt_vals = [""] * n_show

        # 5) lưu vào parent_tab
        if not hasattr(self.parent_tab, "models_by_target"):
            self.parent_tab.models_by_target = {}
        self.parent_tab.models_by_target.setdefault(y_col, {})
        self.parent_tab.models_by_target[y_col]["LinearRegression"] = {
            "model": model,
            "scaler": scaler,
            "x_cols": x_cols,
            "mae": mae,
            "r2": r2,
            "mse": mse
        }


        # ✅ Update UI metrics + table
        ref = self._ui_refs.get("LinearRegression")
        if ref:
            ref["metrics"].setText(
                f"Metrics (TEST)  |  MAE: {mae:.6f}   MSE: {mse:.6f}   R²: {r2:.6f}   "
                f"|  Target: {y_col}  |  X: {len(x_cols)}"
            )

            tbl = ref["table"]
            tbl.setRowCount(n_show)
            for i in range(n_show):
                tbl.setItem(i, 0, QTableWidgetItem(str(dt_vals[i])))
                tbl.setItem(i, 1, QTableWidgetItem(f"{float(y_true_show[i]):.6f}"))
                tbl.setItem(i, 2, QTableWidgetItem(f"{float(y_pred_show[i]):.6f}"))
                tbl.setItem(i, 3, QTableWidgetItem(f"{float(err_show[i]):.6f}"))
            tbl.resizeColumnsToContents()
            tbl.resizeRowsToContents()

        # (tuỳ anh) vẫn giữ messagebox nhỏ gọn
        QMessageBox.information(
            self, "Train OK",
            f"LinearRegression | Target: {y_col}\nMAE: {mae:.6f} | R²: {r2:.6f}\nĐã cập nhật bảng Actual vs Prediction bên dưới."
        )

