"""
Forecasting Tab — dự đoán suy giảm thiết bị nhà máy điện (Equipment Degradation Forecasting).

Thuật toán hỗ trợ:
  - Polynomial Trend   : Khớp đa thức — tốt nhất cho 1 chu kỳ vận hành duy nhất
  - Exponential Decay  : Suy giảm mũ — khi tốc độ bẩn tăng dần phi tuyến
  - Linear (Load-Norm) : Tuyến tính chuẩn hoá theo tải MW — đơn giản, dễ giải thích
  - XGBoost            : Phi tuyến với lag/degradation features — khi có nhiều chu kỳ
  - LightGBM           : Tương tự XGBoost nhưng nhanh hơn 3-5×, dataset lớn

Luồng xử lý:
  1. Lọc dữ liệu theo ngưỡng tải MW (loại bỏ chế độ khởi/ngừng máy)
  2. (Tuỳ chọn) Chuẩn hoá DP theo MW về mức tải tham chiếu
  3. Khớp xu hướng suy giảm theo thời gian
  4. Ngoại suy tương lai → tìm thời điểm DP chạm ngưỡng cần vệ sinh
"""
from __future__ import annotations

import tempfile
import warnings
import numpy as np
import pandas as pd
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QCheckBox, QFrame, QSpinBox, QDoubleSpinBox,
    QComboBox, QMessageBox, QSizePolicy, QTabWidget,
    QDialog, QListWidget, QDialogButtonBox,
    QFormLayout, QGroupBox,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

warnings.filterwarnings("ignore")

# ─────────────────────── Algorithm registry ──────────────────────────────────
_ALGORITHMS = [
    "Polynomial Trend",
    "Exponential Decay",
    "Linear (Load-Norm)",
    "XGBoost",
    "LightGBM",
]

_ALGO_DESC = {
    "Polynomial Trend":   "Đa thức bậc n — phù hợp nhất cho 1 chu kỳ vận hành duy nhất",
    "Exponential Decay":  "Suy giảm mũ — khi tốc độ bẩn tăng dần theo thời gian",
    "Linear (Load-Norm)": "Tuyến tính chuẩn hoá tải — đơn giản, dễ giải thích vận hành",
    "XGBoost":            "Phi tuyến với degradation features — khi có nhiều chu kỳ lịch sử",
    "LightGBM":           "Phi tuyến nhanh — tương tự XGBoost, phù hợp dataset lớn",
}

_ML_ALGOS = {"XGBoost", "LightGBM"}

_PLOTLY_CONFIG = {
    "responsive": True,
    "displayModeBar": True,
    "scrollZoom": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["select2d", "lasso2d"],
}


# ─────────────────────── Degradation feature builder ─────────────────────────
def _build_degradation_features(df: pd.DataFrame, target: str,
                                  feature_cols: list, n_lag: int,
                                  mw_col: Optional[str] = None) -> tuple:
    """Tạo lag features + degradation-specific features cho ML models."""
    parts = {}
    all_cols = list(dict.fromkeys([target] + feature_cols))

    # Lag features
    for col in all_cols:
        for lag in range(1, n_lag + 1):
            parts[f"{col}_lag{lag}"] = df[col].shift(lag)

    feat_df = pd.DataFrame(parts, index=df.index)

    # Thêm degradation features
    if mw_col and mw_col in df.columns:
        feat_df["mw_rolling_mean_24"] = df[mw_col].rolling(24, min_periods=1).mean()
        feat_df["mw_rolling_mean_72"] = df[mw_col].rolling(72, min_periods=1).mean()
        feat_df["mw_high_load_ratio"] = (
            (df[mw_col] > df[mw_col].quantile(0.7)).rolling(24, min_periods=1).mean()
        )

    # Tốc độ suy giảm rolling
    target_series = df[target]
    feat_df["dp_slope_24"] = (
        target_series.rolling(24, min_periods=8).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0], raw=True
        )
    )
    feat_df["dp_slope_72"] = (
        target_series.rolling(72, min_periods=24).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0], raw=True
        )
    )

    # Vị trí trong chu kỳ (index tương đối)
    feat_df["time_idx"] = np.arange(len(df))

    return feat_df, list(feat_df.columns)


def _make_ml_model(algo: str):
    if algo == "XGBoost":
        from xgboost import XGBRegressor
        return XGBRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=5,
            subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=0
        )
    if algo == "LightGBM":
        from lightgbm import LGBMRegressor
        return LGBMRegressor(
            n_estimators=300, learning_rate=0.05, num_leaves=31,
            random_state=42, verbose=-1
        )
    raise ValueError(f"Unknown ML algorithm: {algo}")


# ─────────────────────── Target picker dialog ────────────────────────────────
class _TargetDialog(QDialog):
    def __init__(self, columns: list[str], current: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Target Variable")
        self.setMinimumSize(300, 400)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Select the variable to forecast:"))
        self._list = QListWidget()
        self._list.addItems(columns)
        self._list.setCurrentRow(columns.index(current) if current in columns else 0)
        self._list.itemDoubleClicked.connect(self.accept)
        lay.addWidget(self._list)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def selected(self) -> str:
        item = self._list.currentItem()
        return item.text() if item else ""


# ─────────────────────── Input variables dialog ──────────────────────────────
class _InputVarsDialog(QDialog):
    def __init__(self, columns: list[str], checked: set[str], target: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Input Variables (Features)")
        self.setMinimumSize(320, 480)
        lay = QVBoxLayout(self)

        note = QLabel(
            f"Target: <b>{target}</b><br>"
            f"<span style='color:#1976d2'>💡 Gợi ý: Chọn NET_MW làm input chính "
            f"để model học ảnh hưởng của tải lên suy giảm.</span>"
        )
        note.setWordWrap(True)
        lay.addWidget(note)

        btn_row = QHBoxLayout()
        btn_all  = QPushButton("Select All")
        btn_none = QPushButton("Clear All")
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        lay.addLayout(btn_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.StyledPanel)
        container = QWidget()
        self._chk_lay = QVBoxLayout(container)
        self._chk_lay.setContentsMargins(8, 8, 8, 8)
        self._chk_lay.setSpacing(3)
        scroll.setWidget(container)
        lay.addWidget(scroll, 1)

        self._checkboxes: list[QCheckBox] = []
        for col in columns:
            if col == target:
                continue
            cb = QCheckBox(col)
            cb.setChecked(col in checked)
            self._chk_lay.addWidget(cb)
            self._checkboxes.append(cb)
        self._chk_lay.addStretch()

        btn_all.clicked.connect(lambda: [cb.setChecked(True)  for cb in self._checkboxes])
        btn_none.clicked.connect(lambda: [cb.setChecked(False) for cb in self._checkboxes])

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def selected(self) -> set[str]:
        return {cb.text() for cb in self._checkboxes if cb.isChecked()}


# ─────────────────────── Settings dialog ─────────────────────────────────────
class _SettingsDialog(QDialog):
    def __init__(self, settings: dict, numeric_cols: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Degradation Forecasting Settings")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)

        # ── Algorithm ────────────────────────────────────────────────────────
        grp_algo = QGroupBox("Algorithm")
        algo_lay = QVBoxLayout(grp_algo)
        self._cb_algo = QComboBox()
        for name in _ALGORITHMS:
            self._cb_algo.addItem(name)
            self._cb_algo.setItemData(
                self._cb_algo.count() - 1, _ALGO_DESC[name], Qt.ToolTipRole
            )
        self._cb_algo.setCurrentText(settings.get("algo", "Polynomial Trend"))
        self._cb_algo.currentTextChanged.connect(self._on_algo_changed)
        algo_lay.addWidget(self._cb_algo)

        # ── Polynomial settings ───────────────────────────────────────────────
        self._poly_grp = QGroupBox("Polynomial Trend — Bậc đa thức")
        poly_lay = QFormLayout(self._poly_grp)
        self._spin_degree = QSpinBox()
        self._spin_degree.setRange(1, 5)
        self._spin_degree.setValue(settings.get("poly_degree", 2))
        self._spin_degree.setToolTip(
            "1=Tuyến tính  |  2=Bậc 2 (thường đủ)  |  3=Bậc 3 (phức tạp hơn)"
        )
        poly_lay.addRow("Bậc (degree):", self._spin_degree)
        algo_lay.addWidget(self._poly_grp)

        # ── ML settings ───────────────────────────────────────────────────────
        self._ml_grp = QGroupBox("ML — Lag Features")
        ml_lay = QFormLayout(self._ml_grp)
        self._spin_lag = QSpinBox()
        self._spin_lag.setRange(1, 500)
        self._spin_lag.setValue(settings.get("n_lag", 48))
        self._spin_lag.setToolTip("Số bước quá khứ dùng làm lag features")
        ml_lay.addRow("Lag features:", self._spin_lag)
        self._spin_ratio = QDoubleSpinBox()
        self._spin_ratio.setRange(0.5, 0.95)
        self._spin_ratio.setValue(settings.get("ratio", 0.8))
        self._spin_ratio.setDecimals(2)
        self._spin_ratio.setSingleStep(0.05)
        ml_lay.addRow("Train ratio:", self._spin_ratio)
        algo_lay.addWidget(self._ml_grp)

        lay.addWidget(grp_algo)

        # ── Degradation / Filtering settings ─────────────────────────────────
        grp_deg = QGroupBox("Cài đặt Suy giảm & Lọc dữ liệu")
        deg_lay = QFormLayout(grp_deg)

        # MW column selector
        self._cb_mw_col = QComboBox()
        self._cb_mw_col.addItem("(None)")
        for col in numeric_cols:
            self._cb_mw_col.addItem(col)
        saved_mw = settings.get("mw_col", "")
        idx = self._cb_mw_col.findText(saved_mw) if saved_mw else 0
        self._cb_mw_col.setCurrentIndex(max(0, idx))
        self._cb_mw_col.setToolTip("Chọn cột công suất MW để lọc và chuẩn hoá")
        deg_lay.addRow("Cột tải MW:", self._cb_mw_col)

        self._spin_mw_min = QDoubleSpinBox()
        self._spin_mw_min.setRange(0, 9999)
        self._spin_mw_min.setValue(settings.get("mw_min_threshold", 400.0))
        self._spin_mw_min.setDecimals(1)
        self._spin_mw_min.setSingleStep(50)
        self._spin_mw_min.setToolTip(
            "Loại bỏ dữ liệu khi tải < ngưỡng này (khởi động, ngừng máy, tải thấp)"
        )
        deg_lay.addRow("Lọc tải tối thiểu (MW):", self._spin_mw_min)

        # Normalize by MW
        self._chk_normalize = QCheckBox("Chuẩn hoá DP theo tải MW")
        self._chk_normalize.setChecked(settings.get("normalize_by_mw", False))
        self._chk_normalize.setToolTip(
            "DP_norm = DP × (MW_ref / MW_hiện_tại)\n"
            "Loại bỏ ảnh hưởng của tải → chỉ còn trend suy giảm thuần tuý"
        )
        deg_lay.addRow("", self._chk_normalize)
        self._chk_normalize.toggled.connect(self._on_normalize_toggled)

        self._spin_mw_ref = QDoubleSpinBox()
        self._spin_mw_ref.setRange(1, 9999)
        self._spin_mw_ref.setValue(settings.get("mw_ref", 600.0))
        self._spin_mw_ref.setDecimals(1)
        self._spin_mw_ref.setSingleStep(50)
        self._spin_mw_ref.setToolTip("Mức tải tham chiếu để chuẩn hoá (thường = tải định mức)")
        self._lbl_mw_ref = QLabel("MW tham chiếu:")
        deg_lay.addRow(self._lbl_mw_ref, self._spin_mw_ref)
        self._on_normalize_toggled(self._chk_normalize.isChecked())

        # Wash threshold
        self._spin_wash_threshold = QDoubleSpinBox()
        self._spin_wash_threshold.setRange(-1e6, 1e6)
        self._spin_wash_threshold.setValue(settings.get("wash_threshold", -4.0))
        self._spin_wash_threshold.setDecimals(4)
        self._spin_wash_threshold.setSingleStep(0.1)
        self._spin_wash_threshold.setToolTip(
            "Ngưỡng DP cần vệ sinh (wash threshold)\n"
            "Khi DP dự đoán chạm giá trị này → cần vệ sinh bộ sấy"
        )
        deg_lay.addRow("Ngưỡng vệ sinh (DP):", self._spin_wash_threshold)

        lay.addWidget(grp_deg)

        # ── Forecast horizon ──────────────────────────────────────────────────
        grp_fc = QGroupBox("Thông số Dự báo")
        fc_lay = QFormLayout(grp_fc)

        self._spin_horizon = QSpinBox()
        self._spin_horizon.setRange(1, 5000)
        self._spin_horizon.setValue(settings.get("horizon", 720))
        self._spin_horizon.setToolTip("Số bước dự báo tối đa (vd: 720 = 30 ngày nếu data 1h/điểm)")
        fc_lay.addRow("Forecast steps (tối đa):", self._spin_horizon)

        lay.addWidget(grp_fc)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self._on_algo_changed(self._cb_algo.currentText())

    def _on_algo_changed(self, algo: str):
        self._poly_grp.setVisible(algo in ("Polynomial Trend", "Exponential Decay",
                                            "Linear (Load-Norm)"))
        self._ml_grp.setVisible(algo in _ML_ALGOS)
        if algo == "Polynomial Trend":
            self._poly_grp.setTitle("Polynomial Trend — Bậc đa thức")
        elif algo == "Exponential Decay":
            self._poly_grp.setTitle("Exponential Decay — Không có tham số thêm")
        elif algo == "Linear (Load-Norm)":
            self._poly_grp.setTitle("Linear — Không có tham số thêm")

    def _on_normalize_toggled(self, checked: bool):
        self._spin_mw_ref.setVisible(checked)
        self._lbl_mw_ref.setVisible(checked)

    def get_settings(self) -> dict:
        mw_col_text = self._cb_mw_col.currentText()
        return {
            "algo":              self._cb_algo.currentText(),
            "poly_degree":       self._spin_degree.value(),
            "n_lag":             self._spin_lag.value(),
            "ratio":             self._spin_ratio.value(),
            "mw_col":            mw_col_text if mw_col_text != "(None)" else "",
            "mw_min_threshold":  self._spin_mw_min.value(),
            "normalize_by_mw":   self._chk_normalize.isChecked(),
            "mw_ref":            self._spin_mw_ref.value(),
            "wash_threshold":    self._spin_wash_threshold.value(),
            "horizon":           self._spin_horizon.value(),
        }


# ─────────────────────── Metric card widget ──────────────────────────────────
class _MetricCard(QFrame):
    def __init__(self, label: str, bg: str, fg: str = "white", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumWidth(110)
        self.setMaximumHeight(72)
        self.setStyleSheet(
            f"QFrame{{background:{bg};border-radius:8px;border:none;}}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(1)

        self._lbl_title = QLabel(label)
        self._lbl_title.setAlignment(Qt.AlignCenter)
        self._lbl_title.setStyleSheet(
            f"color:rgba(255,255,255,0.85);font-size:10px;font-weight:500;"
            f"background:transparent;border:none;"
        )
        lay.addWidget(self._lbl_title)

        self._lbl_value = QLabel("—")
        self._lbl_value.setAlignment(Qt.AlignCenter)
        self._lbl_value.setStyleSheet(
            f"color:{fg};font-size:16px;font-weight:bold;"
            f"background:transparent;border:none;"
        )
        lay.addWidget(self._lbl_value)

    def set_value(self, value: str):
        self._lbl_value.setText(value)


# ─────────────────────── Main widget ─────────────────────────────────────────
class ForecastingTab(QWidget):
    """Dự báo suy giảm thiết bị (Equipment Degradation Forecasting) cho nhà máy điện."""

    _TIME_LIKE = {"datetime", "date", "time", "timestamp", "index", "unnamed"}

    def __init__(self, df_provider=None, parent=None):
        super().__init__(parent)
        self.df_provider = df_provider
        self._df: Optional[pd.DataFrame] = None
        self._numeric_cols: list[str] = []
        self._target: str = ""
        self._input_vars: set[str] = set()
        self._settings: dict = {
            "algo": "Polynomial Trend",
            "poly_degree": 2,
            "n_lag": 48,
            "ratio": 0.8,
            "mw_col": "",
            "mw_min_threshold": 400.0,
            "normalize_by_mw": False,
            "mw_ref": 600.0,
            "wash_threshold": -4.0,
            "horizon": 720,
        }
        self._tmp_files: list[str] = []
        self._build_ui()

    # ─────────────────────── UI build ────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setFrameShape(QFrame.StyledPanel)
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(8, 6, 8, 6)
        tb_lay.setSpacing(8)

        _btn_style = (
            "QPushButton{padding:6px 14px;border:1px solid #b0bec5;"
            "border-radius:5px;background:#f5f5f5;font-weight:500;}"
            "QPushButton:hover{background:#e3f2fd;border-color:#1976d2;color:#1976d2;}"
        )

        self._btn_target = QPushButton("🎯  Target Variable")
        self._btn_target.setStyleSheet(_btn_style)
        self._btn_target.setToolTip("Chọn biến cần dự báo (vd: DP_AH)")
        self._btn_target.clicked.connect(self._on_pick_target)
        tb_lay.addWidget(self._btn_target)

        self._btn_inputs = QPushButton("📊  Input Variables")
        self._btn_inputs.setStyleSheet(_btn_style)
        self._btn_inputs.setToolTip("Chọn biến đầu vào (gợi ý: NET_MW)")
        self._btn_inputs.clicked.connect(self._on_pick_inputs)
        tb_lay.addWidget(self._btn_inputs)

        self._btn_settings = QPushButton("⚙️  Settings")
        self._btn_settings.setStyleSheet(_btn_style)
        self._btn_settings.setToolTip("Cấu hình thuật toán, lọc tải, ngưỡng vệ sinh")
        self._btn_settings.clicked.connect(self._on_settings)
        tb_lay.addWidget(self._btn_settings)

        tb_lay.addStretch()

        self._lbl_status = QLabel("No data loaded")
        self._lbl_status.setStyleSheet("color:gray;font-size:11px;")
        tb_lay.addWidget(self._lbl_status)

        tb_lay.addStretch()

        self._btn_train = QPushButton("▶  Train && Forecast")
        self._btn_train.setStyleSheet(
            "QPushButton{background:#1976d2;color:white;padding:7px 18px;"
            "border-radius:5px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#1565c0;}"
            "QPushButton:disabled{background:#b0bec5;}"
        )
        self._btn_train.clicked.connect(self._on_run)
        tb_lay.addWidget(self._btn_train)

        root.addWidget(toolbar)

        # ── Metrics panel ─────────────────────────────────────────────────────
        self._metrics_panel = self._build_metrics_panel()
        root.addWidget(self._metrics_panel)

        # ── Chart tabs ────────────────────────────────────────────────────────
        self._chart_tabs = QTabWidget()
        self._view_forecast   = self._make_webview()
        self._view_trainfit   = self._make_webview()
        self._view_importance = self._make_webview()
        self._chart_tabs.addTab(self._view_forecast,   "📈  Forecast")
        self._chart_tabs.addTab(self._view_trainfit,   "🔍  Train / Test Fit")
        self._chart_tabs.addTab(self._build_importance_tab(), "🏆  Feature Importance")
        root.addWidget(self._chart_tabs, 1)

    def _build_metrics_panel(self) -> QFrame:
        panel = QFrame()
        panel.setVisible(False)
        panel.setStyleSheet(
            "QFrame{background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;}"
        )
        lay = QHBoxLayout(panel)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)

        self._lbl_algo_info = QLabel("")
        self._lbl_algo_info.setStyleSheet(
            "color:#495057;font-size:11px;font-weight:500;"
            "background:transparent;border:none;"
        )
        self._lbl_algo_info.setWordWrap(True)
        lay.addWidget(self._lbl_algo_info, 1)

        self._card_mae       = _MetricCard("MAE",              "#1976d2")
        self._card_rmse      = _MetricCard("RMSE",             "#388e3c")
        self._card_r2        = _MetricCard("R²",               "#7b1fa2")
        self._card_mape      = _MetricCard("MAPE",             "#f57c00")
        self._card_train     = _MetricCard("Train pts",        "#455a64")
        self._card_fc        = _MetricCard("Forecast steps",   "#e53935")
        self._card_wash      = _MetricCard("Wash in (steps)",  "#c62828")

        for card in (self._card_mae, self._card_rmse, self._card_r2, self._card_mape,
                     self._card_train, self._card_fc, self._card_wash):
            lay.addWidget(card)

        return panel

    def _update_metrics(self, algo: str, target: str,
                        mae, rmse, r2, mape,
                        n_train: int, n_forecast: int,
                        wash_step: Optional[int],
                        extra_info: str = ""):
        self._metrics_panel.setVisible(True)
        info = f"<b>{algo}</b>  ▸  Target: <b>{target}</b>"
        if extra_info:
            info += f"  ▸  {extra_info}"
        self._lbl_algo_info.setText(info)
        self._card_mae.set_value(  f"{mae:.4f}"   if mae  is not None else "N/A")
        self._card_rmse.set_value( f"{rmse:.4f}"  if rmse is not None else "N/A")
        self._card_r2.set_value(   f"{r2:.4f}"    if r2   is not None else "N/A")
        self._card_mape.set_value( f"{mape:.2f}%" if mape is not None else "N/A")
        self._card_train.set_value(f"{n_train:,}")
        self._card_fc.set_value(   f"{n_forecast:,}")
        if wash_step is not None:
            self._card_wash.set_value(f"{wash_step:,}")
            self._card_wash.setStyleSheet(
                "QFrame{background:#c62828;border-radius:8px;border:none;}"
            )
        else:
            self._card_wash.set_value("Chưa đạt")
            self._card_wash.setStyleSheet(
                "QFrame{background:#388e3c;border-radius:8px;border:none;}"
            )

    def _build_importance_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        toolbar = QFrame()
        toolbar.setFrameShape(QFrame.StyledPanel)
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(8, 6, 8, 6)
        tb_lay.setSpacing(8)

        lbl = QLabel("Phân tích ảnh hưởng lên biến:")
        lbl.setStyleSheet("font-weight:500;")
        tb_lay.addWidget(lbl)

        self._importance_combo = QComboBox()
        self._importance_combo.setMinimumWidth(220)
        tb_lay.addWidget(self._importance_combo)
        tb_lay.addStretch()

        self._btn_calc_importance = QPushButton("🔍  Tính Feature Importance")
        self._btn_calc_importance.setStyleSheet(
            "QPushButton{background:#7b1fa2;color:white;padding:6px 16px;"
            "border-radius:5px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#6a1b9a;}"
            "QPushButton:disabled{background:#b0bec5;}"
        )
        self._btn_calc_importance.clicked.connect(self._on_calc_importance)
        tb_lay.addWidget(self._btn_calc_importance)

        layout.addWidget(toolbar)
        layout.addWidget(self._view_importance, 1)
        return container

    def _make_webview(self) -> QWebEngineView:
        view = QWebEngineView()
        view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return view

    def _render_to_view(self, fig: go.Figure, view: QWebEngineView):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        pio.write_html(fig, file=tmp.name, include_plotlyjs=True, full_html=True,
                       auto_open=False, config=_PLOTLY_CONFIG)
        tmp.close()
        self._tmp_files.append(tmp.name)
        view.load(QUrl.fromLocalFile(tmp.name))

    # ─────────────────────── Data loading ────────────────────────────────────
    def showEvent(self, event):
        super().showEvent(event)
        self._load_data()

    def _load_data(self) -> bool:
        df = self.df_provider() if self.df_provider else None
        if df is None or df.empty:
            self._lbl_status.setText("No data — load data in Data Analyzing tab first")
            self._lbl_status.setStyleSheet("color:#e53935;font-size:11px;")
            return False

        self._df = df.copy()
        self._numeric_cols = [
            c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c])
            and c.lower().strip() not in self._TIME_LIKE
        ]

        if self._target not in self._numeric_cols:
            self._target = self._numeric_cols[0] if self._numeric_cols else ""

        if not self._input_vars:
            self._input_vars = set(self._numeric_cols) - {self._target}

        self._refresh_btn_labels()
        self._update_importance_combo()
        self._lbl_status.setText(
            f"✅  {df.shape[0]:,} rows × {df.shape[1]} cols  |  {len(self._numeric_cols)} numeric"
        )
        self._lbl_status.setStyleSheet("color:#2e7d32;font-size:11px;font-weight:bold;")
        return True

    def _refresh_btn_labels(self):
        self._btn_target.setText(
            f"🎯  Target:  {self._target}" if self._target else "🎯  Target Variable"
        )
        n = len([v for v in self._input_vars if v in self._numeric_cols and v != self._target])
        self._btn_inputs.setText(f"📊  Input Variables  ({n} selected)")

        algo = self._settings.get("algo", "Polynomial Trend")
        h    = self._settings.get("horizon", 720)
        thr  = self._settings.get("wash_threshold", -4.0)
        mw_t = self._settings.get("mw_min_threshold", 400)

        if algo == "Polynomial Trend":
            deg = self._settings.get("poly_degree", 2)
            self._btn_settings.setText(
                f"⚙️  {algo} deg={deg}  |  MW≥{mw_t}  |  Wash@{thr}  |  {h} steps"
            )
        elif algo in _ML_ALGOS:
            lag = self._settings.get("n_lag", 48)
            self._btn_settings.setText(
                f"⚙️  {algo}  |  lag={lag}  |  MW≥{mw_t}  |  Wash@{thr}  |  {h} steps"
            )
        else:
            self._btn_settings.setText(
                f"⚙️  {algo}  |  MW≥{mw_t}  |  Wash@{thr}  |  {h} steps"
            )

    def _update_importance_combo(self):
        if not hasattr(self, "_importance_combo"):
            return
        current = self._importance_combo.currentText()
        self._importance_combo.blockSignals(True)
        self._importance_combo.clear()
        for col in self._numeric_cols:
            self._importance_combo.addItem(col)
        idx = self._importance_combo.findText(current)
        if idx >= 0:
            self._importance_combo.setCurrentIndex(idx)
        elif self._target:
            idx = self._importance_combo.findText(self._target)
            if idx >= 0:
                self._importance_combo.setCurrentIndex(idx)
        self._importance_combo.blockSignals(False)

    # ─────────────────────── Button handlers ─────────────────────────────────
    def _on_pick_target(self):
        if not self._numeric_cols:
            if not self._load_data():
                return
        dlg = _TargetDialog(self._numeric_cols, self._target, self)
        if dlg.exec() == QDialog.Accepted:
            new_target = dlg.selected()
            if new_target and new_target != self._target:
                self._input_vars.discard(new_target)
                if self._target:
                    self._input_vars.add(self._target)
                self._target = new_target
                self._refresh_btn_labels()

    def _on_pick_inputs(self):
        if not self._numeric_cols:
            if not self._load_data():
                return
        dlg = _InputVarsDialog(self._numeric_cols, self._input_vars, self._target, self)
        if dlg.exec() == QDialog.Accepted:
            self._input_vars = dlg.selected()
            self._refresh_btn_labels()

    def _on_settings(self):
        if not self._numeric_cols:
            self._load_data()
        dlg = _SettingsDialog(self._settings, self._numeric_cols, self)
        if dlg.exec() == QDialog.Accepted:
            self._settings = dlg.get_settings()
            self._refresh_btn_labels()

    def _on_calc_importance(self):
        if not self._load_data():
            return
        if not self._numeric_cols:
            QMessageBox.warning(self, "No Data", "Không có cột numeric nào.")
            return

        analysis_target = self._importance_combo.currentText()
        if not analysis_target:
            QMessageBox.warning(self, "Chưa chọn biến", "Vui lòng chọn biến cần phân tích.")
            return

        features = [c for c in self._numeric_cols if c != analysis_target]
        if not features:
            QMessageBox.warning(self, "Không đủ biến", "Cần ít nhất 2 cột numeric.")
            return

        df_work = self._df[[analysis_target] + features].dropna()
        if len(df_work) < 20:
            QMessageBox.warning(self, "Ít dữ liệu", "Cần ít nhất 20 hàng dữ liệu.")
            return

        self._btn_calc_importance.setEnabled(False)
        self._btn_calc_importance.setText("Đang tính...")
        try:
            X = df_work[features].values
            y = df_work[analysis_target].values

            importances = None
            algo_label  = ""
            try:
                from xgboost import XGBRegressor
                mdl = XGBRegressor(n_estimators=100, max_depth=4,
                                   learning_rate=0.1, random_state=42, verbosity=0)
                mdl.fit(X, y)
                importances = mdl.feature_importances_
                algo_label  = "XGBoost"
            except ImportError:
                pass

            if importances is None:
                try:
                    from lightgbm import LGBMRegressor
                    mdl = LGBMRegressor(n_estimators=100, random_state=42, verbose=-1)
                    mdl.fit(X, y)
                    importances = mdl.feature_importances_
                    algo_label  = "LightGBM"
                except ImportError:
                    pass

            if importances is None:
                from sklearn.ensemble import RandomForestRegressor
                mdl = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
                mdl.fit(X, y)
                importances = mdl.feature_importances_
                algo_label  = "RandomForest"

            self._plot_importance(
                features, importances,
                f"{algo_label} — Ảnh hưởng lên [{analysis_target}]"
            )
            self._chart_tabs.setCurrentIndex(2)

        except Exception:
            import traceback
            QMessageBox.critical(self, "Lỗi Feature Importance", traceback.format_exc())
        finally:
            self._btn_calc_importance.setEnabled(True)
            self._btn_calc_importance.setText("🔍  Tính Feature Importance")

    # ─────────────────────── Preprocess helpers ──────────────────────────────
    def _preprocess(self, df_work: pd.DataFrame, target: str) -> tuple[pd.DataFrame, str, str]:
        """
        Lọc theo MW threshold và (tuỳ chọn) chuẩn hoá DP theo tải.
        Trả về (df_filtered, target_col_used, label_suffix).
        """
        s = self._settings
        mw_col  = s.get("mw_col", "")
        mw_min  = s.get("mw_min_threshold", 0.0)
        norm    = s.get("normalize_by_mw", False)
        mw_ref  = s.get("mw_ref", 600.0)

        df = df_work.copy()
        label = ""

        # Lọc theo tải tối thiểu
        if mw_col and mw_col in df.columns and mw_min > 0:
            before = len(df)
            df = df[df[mw_col] >= mw_min].copy()
            label += f"  |  Lọc MW≥{mw_min} ({before - len(df):,} pts bỏ)"

        # Chuẩn hoá DP theo MW
        target_used = target
        if norm and mw_col and mw_col in df.columns:
            norm_col = f"{target}_norm"
            df[norm_col] = df[target] * (mw_ref / df[mw_col].replace(0, np.nan))
            df = df.dropna(subset=[norm_col])
            target_used = norm_col
            label += f"  |  DP chuẩn hoá (MW_ref={mw_ref})"

        return df.reset_index(drop=True), target_used, label

    # ─────────────────────── Run dispatcher ──────────────────────────────────
    def _on_run(self):
        if not self._load_data():
            return
        if not self._target:
            QMessageBox.warning(self, "No Target", "Please select a target variable first.")
            return

        algo = self._settings["algo"]
        self._btn_train.setEnabled(False)
        self._btn_train.setText("Running...")
        try:
            if algo == "Polynomial Trend":
                self._run_stat_trend(method="poly")
            elif algo == "Exponential Decay":
                self._run_stat_trend(method="exp")
            elif algo == "Linear (Load-Norm)":
                self._run_stat_trend(method="linear")
            elif algo in _ML_ALGOS:
                features = [v for v in self._input_vars
                            if v in self._numeric_cols and v != self._target]
                self._run_degradation_ml(algo, features)
            else:
                QMessageBox.warning(self, "Unknown", f"Unknown algorithm: {algo}")
        except ImportError as e:
            pkg = str(e).split("'")[1] if "'" in str(e) else str(e)
            QMessageBox.critical(self, "Missing Library",
                                 f"Please install:  pip install {pkg}\n\n{e}")
        except Exception:
            import traceback
            QMessageBox.critical(self, "Forecasting Error", traceback.format_exc())
        finally:
            self._btn_train.setEnabled(True)
            self._btn_train.setText("▶  Train && Forecast")

    # ─────────────────────── Statistical trend methods ───────────────────────
    def _run_stat_trend(self, method: str):
        """
        Khớp xu hướng suy giảm lên dữ liệu đã lọc/chuẩn hoá.
        method: 'poly' | 'exp' | 'linear'
        """
        from scipy.optimize import curve_fit
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        target = self._target
        s = self._settings
        horizon = s["horizon"]
        ratio   = 0.8

        # Chọn cột đầu vào
        cols_needed = [target]
        mw_col = s.get("mw_col", "")
        if mw_col and mw_col in self._df.columns:
            cols_needed.append(mw_col)

        df_work, target_used, label_suffix = self._preprocess(
            self._df[cols_needed].dropna(), target
        )

        if len(df_work) < 20:
            QMessageBox.warning(self, "Ít dữ liệu",
                                "Sau khi lọc không đủ dữ liệu. "
                                "Hãy giảm ngưỡng MW hoặc kiểm tra lại cột đã chọn.")
            return

        y_all = df_work[target_used].values.astype(float)
        x_all = np.arange(len(y_all), dtype=float)

        n_train = max(10, int(len(y_all) * ratio))
        x_train, y_train = x_all[:n_train], y_all[:n_train]
        x_test,  y_test  = x_all[n_train:], y_all[n_train:]

        algo = s["algo"]
        degree = s.get("poly_degree", 2)

        # ── Fit model ─────────────────────────────────────────────────────────
        try:
            if method == "poly" or method == "linear":
                d = 1 if method == "linear" else degree
                coeffs = np.polyfit(x_train, y_train, deg=d)
                predict_fn = lambda x: np.polyval(coeffs, x)
                model_desc = f"Polynomial deg={d}" if method == "poly" else "Linear"

            elif method == "exp":
                # Hàm suy giảm: a + b * exp(c * t)
                # Init: a ~ min(y), b ~ range(y), c < 0
                y0, y_end = y_train[0], y_train[-1]
                p0 = [y_end, y0 - y_end, -0.001]
                try:
                    popt, _ = curve_fit(
                        lambda t, a, b, c: a + b * np.exp(c * t),
                        x_train, y_train,
                        p0=p0, maxfev=10000,
                        bounds=([-np.inf, -np.inf, -1], [np.inf, np.inf, 0])
                    )
                    predict_fn = lambda x: popt[0] + popt[1] * np.exp(popt[2] * x)
                    model_desc = f"Exp Decay  a={popt[0]:.3f} b={popt[1]:.3f} c={popt[2]:.5f}"
                except RuntimeError:
                    # Fallback to polynomial deg 2 nếu exp không converge
                    coeffs = np.polyfit(x_train, y_train, deg=2)
                    predict_fn = lambda x: np.polyval(coeffs, x)
                    model_desc = "Polynomial deg=2 (exp fallback)"
            else:
                raise ValueError(f"Unknown method: {method}")

        except Exception as e:
            QMessageBox.warning(self, "Fit lỗi", f"Không thể khớp mô hình:\n{e}")
            return

        # ── Evaluate on train/test ────────────────────────────────────────────
        y_train_pred = predict_fn(x_train)
        y_test_pred  = predict_fn(x_test) if len(x_test) > 0 else np.array([])

        mae = rmse = r2 = mape = None
        if len(y_test) > 0:
            mae  = float(mean_absolute_error(y_test, y_test_pred))
            rmse = float(np.sqrt(mean_squared_error(y_test, y_test_pred)))
            r2   = float(r2_score(y_test, y_test_pred))
            nz   = y_test != 0
            if nz.sum() > 0:
                mape = float(np.mean(np.abs((y_test[nz] - y_test_pred[nz]) / y_test[nz])) * 100)

        # ── Future forecast ───────────────────────────────────────────────────
        wash_threshold = s["wash_threshold"]
        last_x = x_all[-1]
        going_down = wash_threshold < y_all[-1]

        future_x    = np.arange(last_x + 1, last_x + 1 + horizon)
        future_pred = predict_fn(future_x)

        wash_step = None
        for i, v in enumerate(future_pred):
            if going_down and v <= wash_threshold:
                wash_step = i
                break
            elif not going_down and v >= wash_threshold:
                wash_step = i
                break

        extra = ""
        if wash_step is not None:
            extra = f"✅ Đạt ngưỡng vệ sinh ({wash_threshold}) tại step {wash_step + 1}"
        else:
            extra = f"⚠️ Chưa chạm ngưỡng trong {horizon} bước"

        self._update_metrics(
            algo, f"{target_used}{label_suffix}",
            mae, rmse, r2, mape,
            n_train, len(future_pred), wash_step, extra
        )

        hist_idx = list(x_all)
        self._plot_forecast(
            hist_idx, y_all,
            train_end=n_train - 1,
            train_x=list(x_train), y_train_pred=y_train_pred,
            test_x=list(x_test),   y_test_pred=y_test_pred,
            future_x_arr=list(future_x), future_pred=future_pred,
            algo=f"{algo} [{model_desc}]",
            wash_threshold=wash_threshold,
            wash_step=wash_step,
            target_label=target_used,
        )
        self._plot_train_fit(
            list(x_train), y_train, y_train_pred,
            list(x_test), y_test, y_test_pred,
            f"{algo} [{model_desc}]", mae, rmse, r2, mape,
        )

    # ─────────────────────── ML degradation method ───────────────────────────
    def _run_degradation_ml(self, algo: str, features: list):
        """
        XGBoost/LightGBM với degradation features chuyên biệt.
        Phù hợp khi có nhiều chu kỳ vệ sinh lịch sử.
        """
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        target = self._target
        s      = self._settings
        n_lag  = s["n_lag"]
        ratio  = s["ratio"]
        horizon = s["horizon"]
        mw_col  = s.get("mw_col", "")
        wash_threshold = s["wash_threshold"]

        # Chọn cột
        all_cols = list(dict.fromkeys(
            [target] + features
            + ([mw_col] if mw_col and mw_col in self._df.columns else [])
        ))
        df_work, target_used, label_suffix = self._preprocess(
            self._df[all_cols].dropna(), target
        )

        if len(df_work) < n_lag + 20:
            QMessageBox.warning(self, "Ít dữ liệu",
                                f"Sau lọc còn {len(df_work)} điểm, cần ít nhất {n_lag + 20}.")
            return

        # Cập nhật target_used trong danh sách
        used_features = [f for f in features if f in df_work.columns and f != target_used]
        mw_col_used   = mw_col if mw_col and mw_col in df_work.columns else None

        feat_df, feat_names = _build_degradation_features(
            df_work, target_used, used_features, n_lag, mw_col_used
        )

        # Thêm time_idx như feature
        feat_df["time_idx"] = np.arange(len(df_work), dtype=float)
        feat_names_full = list(feat_df.columns)

        combined = pd.concat([df_work[[target_used]], feat_df], axis=1).dropna()
        n_total  = len(combined)
        n_train  = max(n_lag + 10, int(n_total * ratio))

        target_vals = combined[target_used].values
        feat_array  = combined[feat_names_full].values

        # ── Direct multi-step training ────────────────────────────────────────
        n_direct = max(1, min(horizon, 48, (n_train - n_lag) // 3))
        t_idx    = np.arange(n_train - 1)
        h_idx    = np.arange(1, n_direct + 1)
        T_mat, H_mat = np.meshgrid(t_idx, h_idx, indexing="ij")
        valid   = (T_mat + H_mat) < n_train
        T_valid = T_mat[valid]
        H_valid = H_mat[valid]

        if T_valid.size == 0:
            QMessageBox.warning(self, "Không đủ mẫu train",
                                "Hãy giảm n_lag hoặc tăng train ratio.")
            return

        feat_names_h = feat_names_full + ["_step_h"]
        X_train = pd.DataFrame(
            np.column_stack([feat_array[T_valid], H_valid.astype(float)]),
            columns=feat_names_h,
        )
        y_train_arr = target_vals[T_valid + H_valid]

        model = _make_ml_model(algo)
        model.fit(X_train, y_train_arr)

        # 1-step train fit
        X_tr1 = pd.DataFrame(
            np.column_stack([feat_array[:n_train - 1], np.ones(n_train - 1)]),
            columns=feat_names_h,
        )
        y_train_act  = target_vals[1:n_train]
        y_train_pred = model.predict(X_tr1)
        train_x_plot = combined.index[1:n_train].tolist()

        # 1-step test
        if n_total - 1 > n_train:
            X_te = pd.DataFrame(
                np.column_stack([feat_array[n_train:n_total - 1],
                                 np.ones(n_total - 1 - n_train)]),
                columns=feat_names_h,
            )
            y_test_pred = model.predict(X_te)
            y_test_act  = target_vals[n_train + 1:n_total]
            test_x_plot = combined.index[n_train + 1:n_total].tolist()
        else:
            y_test_pred = np.array([])
            y_test_act  = np.array([])
            test_x_plot = []

        # Future forecast — sliding window
        last_feat  = dict(zip(feat_names_full, combined[feat_names_full].iloc[-1].values))
        future_preds = []
        wash_step    = None
        last_val     = float(combined[target_used].iloc[-1])
        going_down   = wash_threshold < last_val

        for step in range(1, horizon + 1):
            row = [last_feat[k] for k in feat_names_full] + [1.0]
            pred = float(model.predict(
                pd.DataFrame([row], columns=feat_names_h))[0])
            future_preds.append(pred)

            # Slide target lags
            for lag in range(n_lag, 1, -1):
                key = f"{target_used}_lag{lag}"
                prev = f"{target_used}_lag{lag - 1}"
                if key in last_feat and prev in last_feat:
                    last_feat[key] = last_feat[prev]
            if f"{target_used}_lag1" in last_feat:
                last_feat[f"{target_used}_lag1"] = pred

            # Cập nhật time_idx
            if "time_idx" in last_feat:
                last_feat["time_idx"] += 1.0

            if wash_step is None:
                if going_down and pred <= wash_threshold:
                    wash_step = step - 1
                    break
                elif not going_down and pred >= wash_threshold:
                    wash_step = step - 1
                    break

        future_preds = np.array(future_preds)

        # Metrics
        mae = rmse = r2 = mape = None
        if len(y_test_act) > 0:
            mae  = float(mean_absolute_error(y_test_act, y_test_pred))
            rmse = float(np.sqrt(mean_squared_error(y_test_act, y_test_pred)))
            r2   = float(r2_score(y_test_act, y_test_pred))
            nz   = y_test_act != 0
            if nz.sum() > 0:
                mape = float(
                    np.mean(np.abs((y_test_act[nz] - y_test_pred[nz]) / y_test_act[nz])) * 100
                )

        extra = ""
        if wash_step is not None:
            extra = f"✅ Đạt ngưỡng vệ sinh ({wash_threshold}) tại step {wash_step + 1}"
        else:
            extra = f"⚠️ Chưa chạm ngưỡng trong {horizon} bước"

        self._update_metrics(
            f"{algo} [Degradation]", f"{target_used}{label_suffix}",
            mae, rmse, r2, mape,
            n_train, len(future_preds), wash_step, extra
        )

        hist_idx  = combined.index.tolist()
        last_x    = hist_idx[-1]
        future_x  = list(range(last_x + 1, last_x + 1 + len(future_preds)))

        self._plot_forecast(
            hist_idx, combined[target_used].values,
            train_end=combined.index[n_train - 1],
            train_x=train_x_plot, y_train_pred=y_train_pred,
            test_x=test_x_plot,   y_test_pred=y_test_pred,
            future_x_arr=future_x, future_pred=future_preds,
            algo=f"{algo} [Degradation]",
            wash_threshold=wash_threshold,
            wash_step=wash_step,
            target_label=target_used,
        )
        self._plot_train_fit(
            train_x_plot, y_train_act, y_train_pred,
            test_x_plot, y_test_act, y_test_pred,
            f"{algo} [Degradation]", mae, rmse, r2, mape,
        )

        # Feature importance
        try:
            raw_model = model if not hasattr(model, "named_steps") else model
            if hasattr(raw_model, "feature_importances_"):
                imp = raw_model.feature_importances_
                self._plot_importance(
                    feat_names_h, imp,
                    f"{algo} — Feature Importance for [{target_used}]"
                )
        except Exception:
            pass

    # ─────────────────────── Plotly charts ───────────────────────────────────
    def _plot_forecast(self, hist_idx, y_hist,
                       train_end,
                       train_x, y_train_pred,
                       test_x,  y_test_pred,
                       future_x_arr, future_pred,
                       algo: str,
                       wash_threshold: Optional[float],
                       wash_step: Optional[int],
                       target_label: str = ""):

        fig = go.Figure()

        # Dữ liệu lịch sử
        fig.add_trace(go.Scatter(
            x=hist_idx, y=y_hist.tolist(),
            mode="lines", name="Dữ liệu thực tế",
            line=dict(color="#1976d2", width=1.5),
            hovertemplate="Step: %{x}<br>Value: %{y:.4f}<extra>Thực tế</extra>",
        ))

        # Train fit
        if len(train_x):
            fig.add_trace(go.Scatter(
                x=list(train_x), y=list(y_train_pred),
                mode="lines", name="Fit (Train)",
                line=dict(color="#f57c00", width=1.5, dash="dot"),
                hovertemplate="Step: %{x}<br>Fit: %{y:.4f}<extra>Train fit</extra>",
            ))

        # Test prediction
        if len(test_x) and len(y_test_pred):
            fig.add_trace(go.Scatter(
                x=list(test_x), y=list(y_test_pred),
                mode="lines", name="Dự đoán (Test)",
                line=dict(color="#388e3c", width=1.5, dash="dash"),
                hovertemplate="Step: %{x}<br>Pred: %{y:.4f}<extra>Test</extra>",
            ))

        # Future forecast — đường nối vào điểm cuối lịch sử
        if future_x_arr and len(future_pred):
            # Điểm nối: last historical → first forecast
            join_x = [hist_idx[-1]] + list(future_x_arr)
            join_y = [float(y_hist[-1])] + list(future_pred)

            fig.add_trace(go.Scatter(
                x=join_x, y=join_y,
                mode="lines", name=f"Dự báo ({len(future_pred)} bước)",
                line=dict(color="#e53935", width=2.5),
                hovertemplate="Step: %{x}<br>Dự báo: %{y:.4f}<extra>Forecast</extra>",
            ))

            # Vùng forecast
            fig.add_vrect(
                x0=hist_idx[-1], x1=future_x_arr[-1],
                fillcolor="rgba(229,57,53,0.05)", line_width=0,
                annotation_text="Vùng dự báo",
                annotation_position="top left",
                annotation_font_size=10, annotation_font_color="#e53935",
            )

        # Ngưỡng vệ sinh
        if wash_threshold is not None:
            fig.add_hline(
                y=wash_threshold,
                line=dict(color="#c62828", width=2, dash="dash"),
                annotation_text=f"🔴 Ngưỡng vệ sinh = {wash_threshold}",
                annotation_position="bottom right",
                annotation_font_color="#c62828",
                annotation_font_size=11,
            )

            # Vùng nguy hiểm (dưới ngưỡng)
            y_min = min(y_hist.min(), wash_threshold - abs(wash_threshold) * 0.1)
            fig.add_hrect(
                y0=y_min, y1=wash_threshold,
                fillcolor="rgba(198,40,40,0.06)", line_width=0,
            )

        # Điểm đạt ngưỡng
        if wash_step is not None and future_x_arr and wash_step < len(future_pred):
            rx = future_x_arr[wash_step]
            ry = float(future_pred[wash_step])
            fig.add_trace(go.Scatter(
                x=[rx], y=[ry],
                mode="markers+text",
                name=f"⚠️ Cần vệ sinh (step {wash_step + 1})",
                marker=dict(size=16, color="#c62828", symbol="star",
                            line=dict(color="white", width=2)),
                text=[f"  Step +{wash_step + 1}<br>  DP={ry:.3f}"],
                textposition="top right",
                textfont=dict(color="#c62828", size=11, family="Arial Black"),
            ))

        # Train/test split
        fig.add_vline(
            x=train_end,
            line=dict(color="#f57c00", width=1.2, dash="dot"),
            annotation_text="Train / Test",
            annotation_position="top right",
            annotation_font_color="#f57c00",
            annotation_font_size=10,
        )

        # Forecast start
        if future_x_arr:
            fig.add_vline(
                x=hist_idx[-1],
                line=dict(color="#7b1fa2", width=1.5, dash="dot"),
                annotation_text="Bắt đầu dự báo",
                annotation_position="top left",
                annotation_font_color="#7b1fa2",
                annotation_font_size=10,
            )

        tgt_display = target_label or self._target
        fig.update_layout(
            title=dict(
                text=f"<b>Degradation Forecast</b>  ·  {algo}  ·  {tgt_display}",
                font=dict(size=14),
            ),
            xaxis_title="Sample index",
            yaxis_title=tgt_display,
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
            hovermode="x unified",
            template="plotly_white",
            margin=dict(l=60, r=30, t=90, b=50),
        )

        self._render_to_view(fig, self._view_forecast)
        self._chart_tabs.setCurrentIndex(0)

    def _plot_train_fit(self, train_x, y_train, y_train_pred,
                        test_x, y_test, y_test_pred, algo,
                        mae=None, rmse=None, r2=None, mape=None):

        has_test = len(test_x) > 0 and len(y_test) > 0
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=False,
            row_heights=[0.62, 0.38],
            subplot_titles=["Thực tế vs Dự đoán", "Residuals (Test)"],
            vertical_spacing=0.12,
        )

        fig.add_trace(go.Scatter(
            x=list(train_x), y=list(y_train),
            mode="lines", name="Train thực tế",
            line=dict(color="#1976d2", width=1.2),
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=list(train_x), y=list(y_train_pred),
            mode="lines", name="Train fit",
            line=dict(color="#f57c00", width=1.2, dash="dot"),
        ), row=1, col=1)

        if has_test:
            fig.add_trace(go.Scatter(
                x=list(test_x), y=list(y_test),
                mode="lines", name="Test thực tế",
                line=dict(color="#388e3c", width=1.4),
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=list(test_x), y=list(y_test_pred),
                mode="lines", name="Test dự đoán",
                line=dict(color="#e53935", width=1.4, dash="dash"),
            ), row=1, col=1)

            resid  = np.array(y_test) - np.array(y_test_pred[:len(y_test)])
            colors = ["#e53935" if r < 0 else "#1976d2" for r in resid]
            fig.add_trace(go.Bar(
                x=list(range(len(resid))), y=resid.tolist(),
                name="Residuals",
                marker=dict(color=colors, opacity=0.75),
                hovertemplate="Sample %{x}<br>Residual: %{y:.4f}<extra></extra>",
            ), row=2, col=1)
            fig.add_hline(y=0, line=dict(color="gray", width=0.8), row=2, col=1)

        metric_parts = []
        if mae  is not None: metric_parts.append(f"MAE = {mae:.4f}")
        if rmse is not None: metric_parts.append(f"RMSE = {rmse:.4f}")
        if r2   is not None: metric_parts.append(f"R² = {r2:.4f}")
        if mape is not None: metric_parts.append(f"MAPE = {mape:.2f}%")
        metric_str = "   |   ".join(metric_parts) if metric_parts else "No test metrics"

        fig.update_layout(
            title=dict(
                text=f"<b>Train / Test Fit</b>  ·  {algo}"
                     f"<br><span style='font-size:11px;color:#555'>{metric_str}</span>",
                font=dict(size=13),
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            hovermode="x",
            template="plotly_white",
            margin=dict(l=60, r=30, t=110, b=50),
            bargap=0.05,
        )
        fig.update_yaxes(title_text=self._target, row=1, col=1)
        fig.update_xaxes(title_text="Test sample index", row=2, col=1)
        fig.update_yaxes(title_text="Residual", row=2, col=1)

        self._render_to_view(fig, self._view_trainfit)

    def _plot_importance(self, feat_names, importances, title: str):
        n_show = min(25, len(feat_names))
        order  = np.argsort(importances)[-n_show:]
        names  = [feat_names[i] for i in order]
        vals   = [float(importances[i]) for i in order]
        total  = sum(vals) or 1.0
        pcts   = [v / total * 100 for v in vals]
        norm   = [v / max(vals) for v in vals]
        colors = [
            f"rgba({int(25 + 200*(1-n))},{int(118 + 80*n)},{int(210 - 10*n)},0.85)"
            for n in norm
        ]
        fig = go.Figure(go.Bar(
            x=vals, y=names,
            orientation="h",
            marker=dict(color=colors),
            customdata=pcts,
            hovertemplate="<b>%{y}</b><br>Importance: %{x:.6f}<br>Share: %{customdata:.1f}%<extra></extra>",
            text=[f"{p:.1f}%" for p in pcts],
            textposition="outside",
            textfont=dict(size=9),
        ))
        fig.update_layout(
            title=dict(text=f"<b>Feature Importance</b>  ·  {title} (top {n_show})",
                       font=dict(size=14)),
            xaxis_title="Importance score",
            yaxis_title="Feature",
            template="plotly_white",
            margin=dict(l=180, r=80, t=70, b=50),
            height=max(400, n_show * 28 + 120),
        )
        self._render_to_view(fig, self._view_importance)