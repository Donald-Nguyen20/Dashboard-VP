# ML_TAB/Steps/Step6/model_compare_dialog.py
from __future__ import annotations

import os
import pickle

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog
)


class ModelCompareDialog(QDialog):
    """
    Step 6: Model Comparison (general)
    - Matrix view: rows = target, cols = algorithms, cell = chosen metric
    - Works for regression & classification if Step 5 stores metrics in:
        parent_tab.models_by_target[target][algo] = { ... }

    Selection:
    - Double click cell -> store parent_tab.selected_model_for_deploy
    """

    REG_METRICS = ["r2", "rmse", "mse", "mae"]
    CLS_METRICS = ["accuracy", "f1", "precision", "recall", "roc_auc"]

    def __init__(self, parent_tab, parent=None):
        super().__init__(parent)
        self.parent_tab = parent_tab

        self.setWindowTitle("Step 6 - Model Comparison")
        self.resize(1020, 580)

        root = QVBoxLayout(self)

        # ===== Header =====
        header = QHBoxLayout()
        header.addWidget(QLabel("Task:"))
        self.cb_task = QComboBox()
        self.cb_task.addItems(["Auto", "Regression", "Classification"])
        header.addWidget(self.cb_task)

        header.addWidget(QLabel("Metric:"))
        self.cb_metric = QComboBox()
        header.addWidget(self.cb_metric)

        header.addStretch(1)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_table)
        header.addWidget(self.btn_refresh)

        self.btn_set_best = QPushButton("Set Best (Selected Target)")
        self.btn_set_best.clicked.connect(self.set_best_for_selected_target)
        header.addWidget(self.btn_set_best)

        btn_save = QPushButton("Save Selected for Step 7")
        btn_save.clicked.connect(self.save_selected_bundle)
        header.addWidget(btn_save)

        root.addLayout(header)

        # ===== Table =====
        self.tbl = QTableWidget()
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectItems)
        self.tbl.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl.cellDoubleClicked.connect(self.on_cell_double_clicked)
        root.addWidget(self.tbl, 1)

        # ===== Footer =====
        footer = QHBoxLayout()
        self.lbl_info = QLabel("Tip: Double-click a cell to select model for Step 7.")
        footer.addWidget(self.lbl_info)
        footer.addStretch(1)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        footer.addWidget(btn_close)
        root.addLayout(footer)

        # signals
        self.cb_task.currentIndexChanged.connect(self._sync_metric_options)

        # init
        self._sync_metric_options()
        self.load_table()

    # -------------------------
    # Data helpers
    # -------------------------
    def _get_models_by_target(self) -> dict:
        return getattr(self.parent_tab, "models_by_target", {}) or {}

    def _collect_algorithms(self, models_by_target: dict) -> list[str]:
        algos = set()
        for _, algomap in models_by_target.items():
            for algo in algomap.keys():
                algos.add(algo)
        return sorted(list(algos))

    def _infer_task_from_record(self, rec: dict) -> str:
        if not isinstance(rec, dict):
            return "regression"
        t = (rec.get("task") or "").lower().strip()
        if t in ("regression", "classification"):
            return t

        reg_keys = {"r2", "mse", "mae", "rmse"}
        cls_keys = {"accuracy", "f1", "precision", "recall", "roc_auc"}

        if any(k in rec for k in cls_keys):
            return "classification"
        if any(k in rec for k in reg_keys):
            return "regression"
        return "regression"

    def _sync_metric_options(self):
        task_ui = self.cb_task.currentText().strip().lower()

        self.cb_metric.blockSignals(True)
        self.cb_metric.clear()

        if task_ui == "classification":
            self.cb_metric.addItems(self.CLS_METRICS)
            if "f1" in self.CLS_METRICS:
                self.cb_metric.setCurrentText("f1")
        else:
            self.cb_metric.addItems(self.REG_METRICS)
            if "r2" in self.REG_METRICS:
                self.cb_metric.setCurrentText("r2")

        self.cb_metric.blockSignals(False)

    def _is_higher_better(self, metric: str) -> bool:
        m = metric.lower().strip()
        if m in ("r2",):
            return True
        if m in ("mse", "rmse", "mae"):
            return False
        if m in ("accuracy", "f1", "precision", "recall", "roc_auc"):
            return True
        return True

    # -------------------------
    # UI actions
    # -------------------------
    def load_table(self):
        models_by_target = self._get_models_by_target()
        if not models_by_target:
            QMessageBox.information(self, "No data", "Chưa có kết quả train ở Step 5.")
            self.tbl.setRowCount(0)
            self.tbl.setColumnCount(0)
            return

        targets = sorted(list(models_by_target.keys()))
        algos = self._collect_algorithms(models_by_target)

        task_ui = self.cb_task.currentText().strip().lower()
        metric = self.cb_metric.currentText().strip()

        self.tbl.setRowCount(len(targets))
        self.tbl.setColumnCount(len(algos))
        self.tbl.setVerticalHeaderLabels(targets)
        self.tbl.setHorizontalHeaderLabels(algos)

        higher_better = self._is_higher_better(metric)

        for r, y_col in enumerate(targets):
            row_best_c = None
            row_best_val = None

            for c, algo in enumerate(algos):
                rec = models_by_target.get(y_col, {}).get(algo)
                if not rec:
                    item = QTableWidgetItem("—")
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                    self.tbl.setItem(r, c, item)
                    continue

                rec_task = self._infer_task_from_record(rec)

                if task_ui in ("regression", "classification") and rec_task != task_ui:
                    item = QTableWidgetItem("—")
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                    self.tbl.setItem(r, c, item)
                    continue

                val = rec.get(metric, None)
                if val is None:
                    item = QTableWidgetItem("NA")
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                    self.tbl.setItem(r, c, item)
                    continue

                try:
                    fval = float(val)
                    txt = f"{fval:.6f}"
                except Exception:
                    txt = str(val)
                    fval = None

                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, {"target": y_col, "algo": algo, "metric": metric})
                self.tbl.setItem(r, c, item)

                if fval is not None:
                    if row_best_val is None:
                        row_best_val = fval
                        row_best_c = c
                    else:
                        better = (fval > row_best_val) if higher_better else (fval < row_best_val)
                        if better:
                            row_best_val = fval
                            row_best_c = c

            if row_best_c is not None:
                best_item = self.tbl.item(r, row_best_c)
                if best_item:
                    best_item.setText(best_item.text() + "  ★")

        self.tbl.resizeColumnsToContents()
        self.tbl.resizeRowsToContents()

        self.lbl_info.setText(
            f"Viewing: Task={self.cb_task.currentText()} | Metric={metric} "
            f"({'higher' if self._is_higher_better(metric) else 'lower'} is better). "
            "Double-click to select for Step 7."
        )

    def on_cell_double_clicked(self, row: int, col: int):
        item = self.tbl.item(row, col)
        if not item:
            return
        meta = item.data(Qt.UserRole)
        if not meta:
            return

        y_col = meta["target"]
        algo = meta["algo"]

        rec = self._get_models_by_target().get(y_col, {}).get(algo)
        if not rec:
            return

        self.parent_tab.selected_model_for_deploy = {
            "target": y_col,
            "algo": algo,
            "bundle": rec
        }

        metric = self.cb_metric.currentText().strip()
        score = rec.get(metric, "NA")

        QMessageBox.information(
            self, "Selected for Step 7",
            f"Selected model:\nTarget: {y_col}\nAlgorithm: {algo}\n{metric}: {score}"
        )

    def set_best_for_selected_target(self):
        items = self.tbl.selectedItems()
        if not items:
            QMessageBox.warning(self, "No selection", "Hãy chọn 1 ô thuộc target trước.")
            return

        item0 = items[0]
        meta = item0.data(Qt.UserRole)
        if not meta:
            QMessageBox.warning(self, "Invalid", "Ô này không có model.")
            return

        y_col = meta["target"]
        models_by_target = self._get_models_by_target()
        algomap = models_by_target.get(y_col, {})

        task_ui = self.cb_task.currentText().strip().lower()
        metric = self.cb_metric.currentText().strip()
        higher_better = self._is_higher_better(metric)

        best_algo = None
        best_val = None

        for algo, rec in algomap.items():
            if not isinstance(rec, dict):
                continue

            rec_task = self._infer_task_from_record(rec)
            if task_ui in ("regression", "classification") and rec_task != task_ui:
                continue

            v = rec.get(metric, None)
            if v is None:
                continue

            try:
                fval = float(v)
            except Exception:
                continue

            if best_val is None:
                best_val = fval
                best_algo = algo
            else:
                better = (fval > best_val) if higher_better else (fval < best_val)
                if better:
                    best_val = fval
                    best_algo = algo

        if best_algo is None:
            QMessageBox.warning(self, "No best", f"Không tìm được best model cho target {y_col} theo metric {metric}.")
            return

        self.parent_tab.selected_model_for_deploy = {
            "target": y_col,
            "algo": best_algo,
            "bundle": algomap[best_algo]
        }

        QMessageBox.information(
            self, "Best Selected",
            f"Best model for target {y_col}:\nAlgorithm: {best_algo}\n{metric}: {best_val:.6f}"
        )

    # -------------------------
    # Save bundle for Step 7
    # -------------------------
    def save_selected_bundle(self):
        sel = getattr(self.parent_tab, "selected_model_for_deploy", None)
        if not sel:
            QMessageBox.warning(self, "Chưa chọn", "Hãy double-click 1 ô hoặc bấm Set Best trước.")
            return

        y_col = sel["target"]
        algo = sel["algo"]
        rec = sel["bundle"]

        if not isinstance(rec, dict):
            QMessageBox.warning(self, "Invalid", "Bundle không hợp lệ.")
            return

        default_name = f"best_{y_col}_{algo}.pkl".replace(" ", "_")
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save best model bundle", default_name, "Pickle (*.pkl)"
        )
        if not save_path:
            return

        # Detect full multi bundle (AAKR-like)
        is_multilr_full = (
            rec.get("bundle_type") == "multilr_full"
            or ("models_by_feature" in rec and "scaler" in rec and "numeric_cols" in rec)
        )
        is_multilr_feature = (rec.get("bundle_type") == "multilr_feature")

        if is_multilr_full:
            bundle = {
                "task": rec.get("task", "regression"),
                "target": y_col,      # thường là "__RECONSTRUCTION__"
                "algo": algo,
                "bundle_type": "multilr_full",

                "numeric_cols": rec.get("numeric_cols", []),
                "scaler": rec.get("scaler"),
                "models_by_feature": rec.get("models_by_feature", {}),

                "metrics": {
                    "r2": rec.get("r2"),
                    "mae": rec.get("mae"),
                    "mse": rec.get("mse"),
                    "rmse": rec.get("rmse"),
                },
            }
        else:
            bundle = {
                "task": rec.get("task", "regression"),
                "target": y_col,
                "algo": algo,
                "bundle_type": "multilr_feature" if is_multilr_feature else "single_target",

                "x_cols": rec.get("x_cols", []),
                "model": rec.get("model"),
                "scaler": rec.get("scaler"),

                "metrics": {
                    "r2": rec.get("r2"),
                    "mae": rec.get("mae"),
                    "mse": rec.get("mse"),
                    "rmse": rec.get("rmse"),
                },
            }

        try:
            with open(save_path, "wb") as f:
                pickle.dump(bundle, f)
        except Exception as e:
            QMessageBox.critical(self, "Save lỗi", str(e))
            return

        self.parent_tab.last_saved_best_model_path = os.path.abspath(save_path)

        if is_multilr_full:
            n_models = 0
            try:
                n_models = len(bundle.get("models_by_feature", {}) or {})
            except Exception:
                n_models = 0
            QMessageBox.information(self, "Saved", f"Đã lưu MULTI full bundle:\n{save_path}\nFeatures/models: {n_models}")
        else:
            QMessageBox.information(self, "Saved", f"Đã lưu bundle:\n{save_path}")
