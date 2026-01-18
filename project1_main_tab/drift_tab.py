import pandas as pd
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateTimeEdit, QMessageBox, QTableWidgetItem,QDialog, QTableWidget
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QDateTime
import json
import os
import mplcursors
from project1_main_tab.Drift_modules.drift_minmax_varying import MinMaxVaryingDialog
from project1_main_tab.Drift_modules.drift_trend_mk import TrendOverviewDialog

DRIFT_JSON_FILE = 'drift_params.json'

def load_drift_params():
    if os.path.exists(DRIFT_JSON_FILE):
        with open(DRIFT_JSON_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {}

def save_drift_params(params):
    with open(DRIFT_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(params, f, indent=2, ensure_ascii=False)

def merge_params(old_params, new_params):
    merged = old_params.copy()
    for var, load_groups in new_params.items():
        if var not in merged:
            merged[var] = {}
        for group, values in load_groups.items():
            merged[var][group] = values
    return merged


def filter_continuous_anomalies(anomalies, min_len=5):
    """
    Giữ lại các chuỗi anomaly có ít nhất min_len điểm liên tục.
    """
    runs = []
    run = []
    last_idx = -2
    for idx in np.where(anomalies)[0]:
        if idx == last_idx + 1:
            run.append(idx)
        else:
            if len(run) >= min_len:
                runs.extend(run)
            run = [idx]
        last_idx = idx
    if len(run) >= min_len:
        runs.extend(run)
    mask = np.zeros_like(anomalies, dtype=bool)
    mask[runs] = True
    return mask

def assign_load_group(df):
    """
    Gán nhãn nhóm tải 'low' hoặc 'high' vào từng dòng trong DataFrame dựa trên cột 'NET MW'.
    Những dòng không thuộc hai nhóm sẽ bị gán là NaN.
    """
    conditions = [
        df['NET MW'].between(240, 300),
        df['NET MW'].between(600, 700)
    ]
    choices = ['low', 'high']
    df['load_group'] = np.select(conditions, choices, default=np.nan)
    return df


from project1_main_tab.Drift_modules.drift_params_dialog import DriftParamsDialog
from project1_main_tab.Drift_modules.drift_algorithms import (detect_ewma, detect_cusum,detect_extreme_trend)
class DriftMonitorTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = pd.DataFrame()
        self.init_ui()
        self.drift_config = load_drift_params()


    def init_ui(self):
        layout = QVBoxLayout(self)
        # --- Control panel ---
        ctrl = QHBoxLayout()
        # Chọn biến
        self.var_combo = QComboBox()
        ctrl.addWidget(QLabel("Variable:"))
        ctrl.addWidget(self.var_combo)
        # Chọn nhóm tải
        self.load_combo = QComboBox()
        self.load_combo.addItems(['low', 'high'])
        ctrl.addWidget(QLabel("Nhóm tải:"))
        ctrl.addWidget(self.load_combo)
        # Chọn thuật toán
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["EWMA", "CUSUM", "Trendline", "Min/Max varying", "Trend (Mann–Kendall)"])
        ctrl.addWidget(QLabel("Algorithm:"))
        ctrl.addWidget(self.algo_combo)
        # Tham số động (sau có thể mở rộng)
        self.param_btn = QPushButton("⚙️ Params")
        ctrl.addWidget(self.param_btn)
        self.param_btn.clicked.connect(self.open_params_dialog)

        # Run
        self.btn_run = QPushButton("🚀 Run")
        self.btn_run.clicked.connect(self.run_detection)
        ctrl.addWidget(self.btn_run)
        layout.addLayout(ctrl)

        # --- DateTime filter ---
        time_layout = QHBoxLayout()
        self.start_dt = QDateTimeEdit()
        self.end_dt   = QDateTimeEdit()
        for w in (self.start_dt, self.end_dt):
            w.setDisplayFormat("yyyy-MM-dd HH:mm")
            w.setCalendarPopup(True)
        time_layout.addWidget(QLabel("From:"))
        time_layout.addWidget(self.start_dt)
        time_layout.addWidget(QLabel("To:"))
        time_layout.addWidget(self.end_dt)
        layout.addLayout(time_layout)

        # --- Canvas vẽ chart ---
        fig = Figure(figsize=(7,4))
        self.canvas = FigureCanvas(fig)
        self.ax = fig.add_subplot(111)
        self.ax.set_position([0.06, 0.12, 0.92, 0.82])  # Điều chỉnh vị trí của biểu đồ
        layout.addWidget(self.canvas)
    
    def update_variables(self, df: pd.DataFrame):
        self.df = df
        cols = [c for c in df.columns if c.lower() not in ['datetime','date','time','sourcefolder','power','net mw']]
        self.var_combo.clear()
        self.var_combo.addItems(cols)
        # Khởi tạo DateTimeEdit
        if 'Datetime' in df.columns:
            mn = pd.to_datetime(df['Datetime'].min())
            mx = pd.to_datetime(df['Datetime'].max())
            self.start_dt.setDateTime(QDateTime(mn))
            self.end_dt.setDateTime(QDateTime(mx))

    def run_detection(self):
        if self.df.empty:
            QMessageBox.warning(self, "Cảnh báo", "Chưa có dữ liệu.")
            return

        var = self.var_combo.currentText()
        group = self.load_combo.currentText()
        algo = self.algo_combo.currentText()
        df = self.df.copy()

        # Lọc theo thời gian
        start = self.start_dt.dateTime().toPython()
        end = self.end_dt.dateTime().toPython()
        df = df[(df['Datetime'] >= start) & (df['Datetime'] <= end)]

        # --- Nhánh Min/Max varying (giữ nguyên) ---
        if algo == "Min/Max varying":
            if df.empty:
                QMessageBox.warning(self, "Cảnh báo", "Không có dữ liệu trong khoảng thời gian đã chọn.")
                return
            dlg = MinMaxVaryingDialog(df, parent=self)
            dlg.exec()
            return

        # --- Nhánh Trend (Mann–Kendall) mới, dùng chính df đã lọc thời gian ---
        if algo == "Trend (Mann–Kendall)":
            if df.empty:
                QMessageBox.warning(self, "Cảnh báo", "Không có dữ liệu trong khoảng thời gian đã chọn.")
                return
            dlg = TrendOverviewDialog(df, time_col="Datetime", parent=self)
            dlg.exec()
            return

        # --- Các thuật toán còn lại: EWMA, CUSUM, Trendline... ---
        df = assign_load_group(df)
        df = df[df['load_group'] == group]

        if df.empty:
            QMessageBox.warning(self, "Cảnh báo", f"Không có dữ liệu cho nhóm tải '{group}' trong khoảng thời gian đã chọn.")
            return

        config = self.drift_config.get(var, {}).get(group, None)
        if not config:
            QMessageBox.warning(self, "Cảnh báo", f"Chưa cấu hình baseline/k/h cho {var} [{group}]")
            return

        baseline, k, h = config['baseline'], config['k'], config['h']
        df['residual'] = df[var] - baseline

        self.ax.clear()

        if algo == "EWMA":
            lambda_ = config.get('lambda', 0.2)
            L = config.get('L', 3)
            S, ucl, lcl, anomalies = detect_ewma(df['residual'], lambda_, L)

            self.ax.plot(df['Datetime'], df['residual'], label='Residual')
            self.ax.plot(df['Datetime'], S, label='EWMA')
            self.ax.axhline(ucl, color='red', linestyle='--', label='UCL')
            self.ax.axhline(lcl, color='red', linestyle='--', label='LCL')

            scatter = self.ax.scatter(df['Datetime'][anomalies], S[anomalies], color='orange', label='⚠️ EWMA Warning')
            mplcursors.cursor(scatter).connect(
                "add", lambda sel: sel.annotation.set_text(
                    f"{df['Datetime'][anomalies].iloc[sel.index]:%Y-%m-%d %H:%M:%S}\nEWMA Warning")
            )

        elif algo == "CUSUM":
            Cp, Cm, anomalies = detect_cusum(df['residual'], k=k, h=h)
            anomalies_filtered = filter_continuous_anomalies(anomalies, min_len=5)

            self.ax.plot(df['Datetime'], Cp, label='CUSUM+')
            self.ax.plot(df['Datetime'], Cm, label='CUSUM-')

            scatter_cp = self.ax.scatter(df['Datetime'][anomalies_filtered], Cp[anomalies_filtered], color='orange', label='⚠️ CUSUM+')
            mplcursors.cursor(scatter_cp).connect(
                "add", lambda sel: sel.annotation.set_text(
                    f"{df['Datetime'][anomalies_filtered].iloc[sel.index]:%Y-%m-%d %H:%M:%S}\nCUSUM+ Warning")
            )

            scatter_cm = self.ax.scatter(df['Datetime'][anomalies_filtered], Cm[anomalies_filtered], color='purple', label='⚠️ CUSUM−')
            mplcursors.cursor(scatter_cm).connect(
                "add", lambda sel: sel.annotation.set_text(
                    f"{df['Datetime'][anomalies_filtered].iloc[sel.index]:%Y-%m-%d %H:%M:%S}\nCUSUM− Warning")
            )

        elif algo == "Trendline":
            self.ax.plot(df['Datetime'], df[var], label='Original', color='gray', linewidth=0.8)

            # Minima
            minima = detect_extreme_trend(df, var, baseline, direction='down')
            if minima:
                dt_min, val_min = zip(*minima)
                scatter_min = self.ax.scatter(dt_min, val_min, color='blue', label='Minima')
                mplcursors.cursor(scatter_min).connect(
                    "add", lambda sel: sel.annotation.set_text(
                        f"{dt_min[sel.index].strftime('%Y-%m-%d %H:%M:%S')}\nMinima")
                )
                if len(minima) > 1:
                    self.ax.plot(dt_min, val_min, linestyle='--', color='blue', label='Minima Trend')

            # Maxima
            maxima = detect_extreme_trend(df, var, baseline, direction='up')
            if maxima:
                dt_max, val_max = zip(*maxima)
                scatter_max = self.ax.scatter(dt_max, val_max, color='red', label='Maxima')
                mplcursors.cursor(scatter_max).connect(
                    "add", lambda sel: sel.annotation.set_text(
                        f"{dt_max[sel.index].strftime('%Y-%m-%d %H:%M:%S')}\nMaxima")
                )
                if len(maxima) > 1:
                    self.ax.plot(dt_max, val_max, linestyle='--', color='red', label='Maxima Trend')

        else:
            QMessageBox.warning(self, "Lỗi", f"Thuật toán {algo} chưa hỗ trợ.")
            return

        self.ax.legend()
        self.canvas.draw()



    def open_params_dialog(self):
        # Lấy list biến hiện tại
        variables = [self.var_combo.itemText(i) for i in range(self.var_combo.count())]
        dialog = DriftParamsDialog(self.drift_config, variables, parent=self)
        if dialog.exec():
            new_params = dialog.get_params()
            self.drift_config = merge_params(self.drift_config, new_params)
            save_drift_params(self.drift_config)
            QMessageBox.information(self, "Success", "Drift params saved successfully!")



        
