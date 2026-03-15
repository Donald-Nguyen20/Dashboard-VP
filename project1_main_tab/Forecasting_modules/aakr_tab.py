"""
Tab AAKR (Auto-Associative Kernel Regression)
- Phát hiện bất thường trong dữ liệu nhà máy điện
- So sánh giá trị thực vs giá trị tái tạo, tính residuals và anomaly score
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QCheckBox, QFrame, QDoubleSpinBox, QTabWidget,
    QMessageBox, QSplitter, QSizePolicy,
)
from PySide6.QtCore import Qt

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas


# ─────────────────────────────── AAKR core ───────────────────────────────────
def _aakr_reconstruct(X_memory: np.ndarray, X_query: np.ndarray, h: float = 1.0) -> np.ndarray:
    """
    AAKR reconstruction sử dụng Gaussian kernel.
    X_memory : (N, d) - dữ liệu vận hành bình thường (training)
    X_query  : (M, d) - điểm cần tái tạo
    h        : bandwidth (kernel width)
    Trả về   : X_reconstructed (M, d)
    """
    # Xử lý batch để tránh OOM với dataset lớn
    batch = 512
    M = X_query.shape[0]
    result = np.zeros_like(X_query)
    for start in range(0, M, batch):
        end = min(start + batch, M)
        diff = X_query[start:end, None, :] - X_memory[None, :, :]  # (b, N, d)
        dist_sq = np.sum(diff ** 2, axis=-1)                        # (b, N)
        w = np.exp(-dist_sq / (2.0 * h * h))                        # (b, N)
        w_sum = w.sum(axis=1, keepdims=True)
        w_sum = np.maximum(w_sum, 1e-12)
        result[start:end] = (w @ X_memory) / w_sum                 # (b, d)
    return result


# ─────────────────────────────── Widget ──────────────────────────────────────
class AakrTab(QWidget):
    """Tab AAKR: phát hiện bất thường cho dữ liệu nhà máy điện."""

    def __init__(self, df_provider=None, parent=None):
        super().__init__(parent)
        self.df_provider = df_provider
        self._df: Optional[pd.DataFrame] = None
        self._memory: Optional[np.ndarray] = None
        self._checkboxes: list[QCheckBox] = []

        self._build_ui()

    # ──────────────────── UI ─────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Top bar
        top = QHBoxLayout()
        btn_load = QPushButton("📂 Lấy dữ liệu từ Tab 1")
        btn_load.clicked.connect(self._on_load)
        top.addWidget(btn_load)
        self._lbl_status = QLabel("Chưa có dữ liệu")
        self._lbl_status.setStyleSheet("color:gray;")
        top.addWidget(self._lbl_status)
        top.addStretch()
        root.addLayout(top)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        # ── Left panel ──────────────────────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(270)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 8, 0)
        left_lay.setSpacing(6)

        left_lay.addWidget(QLabel("<b>Chọn biến AAKR:</b>"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.StyledPanel)
        chk_container = QWidget()
        self._chk_layout = QVBoxLayout(chk_container)
        self._chk_layout.setContentsMargins(4, 4, 4, 4)
        self._chk_layout.setSpacing(2)
        self._chk_layout.addStretch()
        scroll.setWidget(chk_container)
        left_lay.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_all = QPushButton("Chọn tất cả")
        btn_none = QPushButton("Bỏ tất cả")
        btn_all.clicked.connect(lambda: [cb.setChecked(True) for cb in self._checkboxes])
        btn_none.clicked.connect(lambda: [cb.setChecked(False) for cb in self._checkboxes])
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        left_lay.addLayout(btn_row)

        # Params frame
        pf = QFrame()
        pf.setFrameShape(QFrame.StyledPanel)
        pl = QVBoxLayout(pf)
        pl.setSpacing(6)

        pl.addWidget(QLabel("<b>Tham số:</b>"))

        h_row = QHBoxLayout()
        h_row.addWidget(QLabel("Kernel width (h):"))
        self._spin_h = QDoubleSpinBox()
        self._spin_h.setRange(0.01, 1000.0)
        self._spin_h.setValue(1.0)
        self._spin_h.setDecimals(2)
        self._spin_h.setSingleStep(0.1)
        self._spin_h.setToolTip("Độ rộng kernel Gaussian. Giá trị nhỏ = nhạy hơn; lớn = mịn hơn")
        h_row.addWidget(self._spin_h)
        pl.addLayout(h_row)

        ratio_row = QHBoxLayout()
        ratio_row.addWidget(QLabel("Train ratio:"))
        self._spin_ratio = QDoubleSpinBox()
        self._spin_ratio.setRange(0.1, 0.95)
        self._spin_ratio.setValue(0.7)
        self._spin_ratio.setDecimals(2)
        self._spin_ratio.setSingleStep(0.05)
        self._spin_ratio.setToolTip("Tỷ lệ dữ liệu dùng để training (dữ liệu vận hành bình thường)")
        ratio_row.addWidget(self._spin_ratio)
        pl.addLayout(ratio_row)

        sigma_row = QHBoxLayout()
        sigma_row.addWidget(QLabel("Ngưỡng anomaly (σ):"))
        self._spin_sigma = QDoubleSpinBox()
        self._spin_sigma.setRange(1.0, 10.0)
        self._spin_sigma.setValue(3.0)
        self._spin_sigma.setDecimals(1)
        self._spin_sigma.setSingleStep(0.5)
        self._spin_sigma.setToolTip("Ngưỡng phát hiện bất thường = mean + σ × std của anomaly score")
        sigma_row.addWidget(self._spin_sigma)
        pl.addLayout(sigma_row)

        left_lay.addWidget(pf)

        btn_train = QPushButton("▶  Train & Detect Anomaly")
        btn_train.setStyleSheet(
            "QPushButton{background:#1976d2;color:white;padding:8px;border-radius:4px;font-weight:bold;}"
            "QPushButton:hover{background:#1565c0;}"
        )
        btn_train.clicked.connect(self._on_train)
        left_lay.addWidget(btn_train)

        splitter.addWidget(left)

        # ── Right panel: chart tabs ──────────────────────────────────────────
        self._chart_tabs = QTabWidget()
        self._canvas_recon   = self._make_canvas()
        self._canvas_resid   = self._make_canvas()
        self._canvas_anomaly = self._make_canvas()
        self._chart_tabs.addTab(self._canvas_recon,   "Reconstruction")
        self._chart_tabs.addTab(self._canvas_resid,   "Residuals")
        self._chart_tabs.addTab(self._canvas_anomaly, "Anomaly Score")
        splitter.addWidget(self._chart_tabs)
        splitter.setSizes([270, 900])

    def _make_canvas(self) -> FigureCanvas:
        fig = Figure(figsize=(9, 5), dpi=96)
        fig.patch.set_facecolor("white")
        canvas = FigureCanvas(fig)
        canvas._fig = fig
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return canvas

    # ──────────────────── Data ───────────────────────────────────────────────
    def _on_load(self):
        df = self.df_provider() if self.df_provider else None
        if df is None or df.empty:
            QMessageBox.warning(self, "Không có dữ liệu", "Chưa có dữ liệu từ Tab 1. Hãy load dữ liệu ở tab Data Analyzing trước.")
            return
        self._df = df.copy()
        self._refresh_checkboxes()
        self._lbl_status.setText(f"✅  {df.shape[0]:,} hàng × {df.shape[1]} cột")
        self._lbl_status.setStyleSheet("color:green;font-weight:bold;")

    _TIME_LIKE = {"datetime", "date", "time", "timestamp", "index", "unnamed"}

    def _refresh_checkboxes(self):
        while self._chk_layout.count() > 1:
            item = self._chk_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._checkboxes.clear()
        if self._df is None:
            return
        for col in self._df.columns:
            if col.lower().strip() in self._TIME_LIKE:
                continue
            if not pd.api.types.is_numeric_dtype(self._df[col]):
                continue
            cb = QCheckBox(col)
            cb.setChecked(True)
            self._chk_layout.insertWidget(self._chk_layout.count() - 1, cb)
            self._checkboxes.append(cb)

    def _selected_cols(self) -> list[str]:
        return [cb.text() for cb in self._checkboxes if cb.isChecked()]

    # ──────────────────── Train & Plot ───────────────────────────────────────
    def _on_train(self):
        if self._df is None:
            QMessageBox.warning(self, "Chưa có dữ liệu", "Hãy bấm 'Lấy dữ liệu từ Tab 1' trước.")
            return
        cols = self._selected_cols()
        if not cols:
            QMessageBox.warning(self, "Chưa chọn biến", "Hãy chọn ít nhất 1 biến.")
            return

        try:
            df_clean = self._df[cols].dropna()
            if len(df_clean) < 20:
                QMessageBox.warning(self, "Quá ít dữ liệu", f"Chỉ có {len(df_clean)} hàng hợp lệ sau khi bỏ NaN.")
                return

            X = df_clean.values.astype(float)

            # Normalize (Z-score per column)
            self._mean = X.mean(axis=0)
            self._std  = X.std(axis=0)
            self._std[self._std < 1e-8] = 1.0
            X_norm = (X - self._mean) / self._std

            # Train/test split
            n_train = int(len(X_norm) * self._spin_ratio.value())
            n_train = max(10, n_train)
            X_train = X_norm[:n_train]

            h = self._spin_h.value()

            # Reconstruct toàn bộ dataset với memory = X_train
            X_recon_norm = _aakr_reconstruct(X_train, X_norm, h=h)
            X_recon = X_recon_norm * self._std + self._mean

            residuals = X - X_recon

            # Anomaly score = RMS của normalized residuals (mỗi timestep)
            res_norm = (X - X_recon) / (self._std + 1e-8)
            anomaly_score = np.sqrt(np.mean(res_norm ** 2, axis=1))

            # Tính metrics
            from sklearn.metrics import mean_absolute_error, mean_squared_error
            n_test = len(X) - n_train
            mae = mean_absolute_error(X[n_train:], X_recon[n_train:]) if n_test > 0 else float("nan")
            rmse = np.sqrt(mean_squared_error(X[n_train:], X_recon[n_train:])) if n_test > 0 else float("nan")

            # Ngưỡng anomaly
            sigma = self._spin_sigma.value()
            score_train = anomaly_score[:n_train]
            threshold = score_train.mean() + sigma * score_train.std()
            n_anomaly = int((anomaly_score > threshold).sum())

            self._plot_reconstruction(X, X_recon, cols, n_train)
            self._plot_residuals(residuals, cols, n_train)
            self._plot_anomaly(anomaly_score, n_train, threshold, n_anomaly)

            self._lbl_status.setText(
                f"✅  Train={n_train} | Test={n_test} | MAE={mae:.4f} | RMSE={rmse:.4f} | "
                f"Anomalies={n_anomaly} (σ={sigma})"
            )

        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Lỗi AAKR", traceback.format_exc())

    def _plot_reconstruction(self, X_orig, X_recon, cols, n_train):
        fig = self._canvas_recon._fig
        fig.clear()
        n = min(len(cols), 5)
        for i in range(n):
            ax = fig.add_subplot(n, 1, i + 1)
            ax.plot(X_orig[:, i],  color="#1976d2", lw=0.9, label="Actual")
            ax.plot(X_recon[:, i], color="#e53935", lw=0.9, ls="--", label="Reconstructed (AAKR)")
            ax.axvline(n_train, color="#f57c00", lw=1.2, ls=":", label="Train / Test")
            ax.set_ylabel(cols[i], fontsize=8)
            ax.legend(fontsize=7, loc="upper right", ncol=3)
            ax.tick_params(labelsize=7)
            ax.grid(True, alpha=0.3)
        if len(cols) > 5:
            fig.suptitle(f"AAKR Reconstruction — hiện 5/{len(cols)} biến đầu", fontsize=9)
        else:
            fig.suptitle("AAKR Reconstruction (Actual vs Reconstructed)", fontsize=10)
        fig.tight_layout()
        self._canvas_recon.draw()

    def _plot_residuals(self, residuals, cols, n_train):
        fig = self._canvas_resid._fig
        fig.clear()
        n = min(len(cols), 5)
        for i in range(n):
            ax = fig.add_subplot(n, 1, i + 1)
            ax.plot(residuals[:, i], color="#388e3c", lw=0.9)
            ax.axhline(0, color="gray", lw=0.6)
            ax.axvline(n_train, color="#f57c00", lw=1.2, ls=":")
            ax.set_ylabel(f"Δ {cols[i]}", fontsize=8)
            ax.tick_params(labelsize=7)
            ax.grid(True, alpha=0.3)
        fig.suptitle("Residuals = Actual − Reconstructed", fontsize=10)
        fig.tight_layout()
        self._canvas_resid.draw()

    def _plot_anomaly(self, score, n_train, threshold, n_anomaly):
        fig = self._canvas_anomaly._fig
        fig.clear()
        ax = fig.add_subplot(1, 1, 1)

        x = np.arange(len(score))
        ax.plot(x, score, color="#1976d2", lw=0.9, label="Anomaly score (RMS residual norm)")
        ax.axhline(threshold, color="#e53935", lw=1.4, ls="--",
                   label=f"Threshold = {threshold:.4f}  (mean + {self._spin_sigma.value()}σ)")
        ax.axvline(n_train, color="#f57c00", lw=1.2, ls=":", label="Train / Test")

        mask = score > threshold
        if mask.any():
            ax.scatter(x[mask], score[mask], color="#e53935", s=12, zorder=5,
                       label=f"Anomalies: {n_anomaly}")

        ax.fill_between(x, 0, score, where=mask, color="#e5393533", label="_nolegend_")
        ax.set_xlabel("Sample index", fontsize=9)
        ax.set_ylabel("Anomaly Score", fontsize=9)
        ax.set_title(f"AAKR Anomaly Detection — {n_anomaly} điểm bất thường phát hiện", fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        self._canvas_anomaly.draw()
