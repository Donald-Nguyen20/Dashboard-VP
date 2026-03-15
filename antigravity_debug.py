"""
ANTIGRAVITY AUTO-DEBUG
======================
Tự động kiểm tra các tính năng của Dashboard-VP và gửi báo cáo + đồ thị qua Telegram.

Cách chạy:
    python antigravity_debug.py           # chạy 1 lần ngay lập tức
    python antigravity_debug.py --schedule 60   # chạy mỗi 60 phút

Cấu hình Telegram: antigravity_config.py
"""

import sys
import os
import io
import time
import traceback
import argparse
import importlib
from datetime import datetime
from pathlib import Path

# Thêm project root vào path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "project1_main_tab"))

import requests


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
try:
    from antigravity_config import (
        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
        DATA_PATH, OUTPUT_DIR,
        EWMA_LAMBDA, EWMA_L, CUSUM_K, CUSUM_H, MIN_ANOMALY_LEN,
    )
except ImportError:
    print("[LỖI] Không tìm thấy antigravity_config.py")
    sys.exit(1)

OUTPUT_PATH = ROOT / OUTPUT_DIR
OUTPUT_PATH.mkdir(exist_ok=True)


# ─────────────────────────────────────────────
# Telegram helpers
# ─────────────────────────────────────────────
TELE_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def tele_send_text(text: str) -> bool:
    """Gửi tin nhắn văn bản qua Telegram."""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("[TELEGRAM] (chưa cấu hình) →", text[:120])
        return False
    try:
        r = requests.post(
            f"{TELE_API}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        return r.ok
    except Exception as e:
        print(f"[TELEGRAM] Lỗi gửi text: {e}")
        return False

def tele_send_photo(img_path: Path, caption: str = "") -> bool:
    """Gửi ảnh đồ thị qua Telegram."""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(f"[TELEGRAM] (chưa cấu hình) → ảnh: {img_path.name}")
        return False
    try:
        with open(img_path, "rb") as f:
            r = requests.post(
                f"{TELE_API}/sendPhoto",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                files={"photo": f},
                timeout=30,
            )
        return r.ok
    except Exception as e:
        print(f"[TELEGRAM] Lỗi gửi ảnh: {e}")
        return False

def tele_send_document(doc_path: Path, caption: str = "") -> bool:
    """Gửi file (pdf/html) qua Telegram."""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(f"[TELEGRAM] (chưa cấu hình) → file: {doc_path.name}")
        return False
    try:
        with open(doc_path, "rb") as f:
            r = requests.post(
                f"{TELE_API}/sendDocument",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                files={"document": f},
                timeout=30,
            )
        return r.ok
    except Exception as e:
        print(f"[TELEGRAM] Lỗi gửi file: {e}")
        return False


# ─────────────────────────────────────────────
# Kiểm tra import các module
# ─────────────────────────────────────────────
MODULES_TO_CHECK = [
    ("numpy",                          "numpy"),
    ("pandas",                         "pandas"),
    ("matplotlib",                     "matplotlib"),
    ("PySide6.QtWidgets",              "PySide6"),
    ("Drift_modules.drift_algorithms", "drift_algorithms"),
    ("Plot_modules.heatmap_correlation","heatmap_correlation"),
    ("Plot_modules.histogram_chart",   "histogram_chart"),
    ("Plot_modules.line_chart",        "line_chart"),
    ("Plot_modules.scatter_chart",     "scatter_chart"),
]

def check_imports() -> dict:
    results = {}
    for mod, label in MODULES_TO_CHECK:
        try:
            importlib.import_module(mod)
            results[label] = "✅ OK"
        except Exception as e:
            results[label] = f"❌ {e}"
    return results


# ─────────────────────────────────────────────
# Load dữ liệu mẫu
# ─────────────────────────────────────────────
def load_sample_data():
    import pandas as pd
    csv_path = ROOT / DATA_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"Không tìm thấy: {csv_path}")
    df = pd.read_csv(csv_path)
    # Chuẩn hóa tên cột
    df.columns = [c.strip() for c in df.columns]
    return df


# ─────────────────────────────────────────────
# Chạy drift algorithms và vẽ đồ thị
# ─────────────────────────────────────────────
def run_drift_and_plot(df) -> list[Path]:
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from Drift_modules.drift_algorithms import (
        detect_ewma, detect_cusum, filter_continuous_anomalies
    )

    saved = []

    # Chọn cột số đầu tiên (bỏ qua cột datetime/date/time)
    skip = {"datetime", "date", "time", "sourcefolder", "sourcefile"}
    numeric_cols = [
        c for c in df.columns
        if c.lower() not in skip and pd.api.types.is_numeric_dtype(df[c])
    ]
    if not numeric_cols:
        print("[DRIFT] Không có cột số trong dữ liệu.")
        return saved

    col = numeric_cols[0]
    series = df[col].dropna().reset_index(drop=True)

    if len(series) < 20:
        print("[DRIFT] Dữ liệu quá ngắn để phát hiện drift.")
        return saved

    # Tính residual (series - mean)
    residual = series - series.mean()

    # ── EWMA ──
    try:
        S, ucl, lcl, anomalies_ewma = detect_ewma(residual, EWMA_LAMBDA, EWMA_L)
        anomalies_ewma = filter_continuous_anomalies(anomalies_ewma, MIN_ANOMALY_LEN)

        fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
        fig.suptitle(f"EWMA Drift Detection — {col}", fontsize=13, fontweight="bold")

        ax0 = axes[0]
        ax0.plot(series.values, color="#2196F3", linewidth=0.9, label="Giá trị thực")
        ax0.scatter(
            np.where(anomalies_ewma)[0], series.values[anomalies_ewma],
            color="red", s=18, zorder=5, label="Anomaly"
        )
        ax0.set_ylabel(col)
        ax0.legend(fontsize=8)
        ax0.grid(alpha=0.3)

        ax1 = axes[1]
        ax1.plot(S, color="#FF9800", linewidth=0.9, label="EWMA")
        ax1.axhline(ucl, color="red",   linestyle="--", linewidth=0.8, label=f"UCL={ucl:.3f}")
        ax1.axhline(lcl, color="green", linestyle="--", linewidth=0.8, label=f"LCL={lcl:.3f}")
        ax1.scatter(np.where(anomalies_ewma)[0], S[anomalies_ewma], color="red", s=18, zorder=5)
        ax1.set_ylabel("EWMA")
        ax1.set_xlabel("Điểm thời gian")
        ax1.legend(fontsize=8)
        ax1.grid(alpha=0.3)

        plt.tight_layout()
        out = OUTPUT_PATH / "ewma_drift.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        saved.append(out)
        print(f"[DRIFT] EWMA → {out.name} (anomalies: {anomalies_ewma.sum()})")
    except Exception as e:
        print(f"[DRIFT] EWMA lỗi: {e}")

    # ── CUSUM ──
    try:
        Cp, Cm, anomalies_cusum = detect_cusum(residual, CUSUM_K, CUSUM_H)
        anomalies_cusum = filter_continuous_anomalies(anomalies_cusum, MIN_ANOMALY_LEN)

        fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
        fig.suptitle(f"CUSUM Drift Detection — {col}", fontsize=13, fontweight="bold")

        ax0 = axes[0]
        ax0.plot(series.values, color="#2196F3", linewidth=0.9, label="Giá trị thực")
        ax0.scatter(
            np.where(anomalies_cusum)[0], series.values[anomalies_cusum],
            color="red", s=18, zorder=5, label="Anomaly"
        )
        ax0.set_ylabel(col)
        ax0.legend(fontsize=8)
        ax0.grid(alpha=0.3)

        ax1 = axes[1]
        ax1.plot(Cp, color="#4CAF50", linewidth=0.9, label="CUSUM+")
        ax1.plot(Cm, color="#F44336", linewidth=0.9, label="CUSUM−")
        ax1.axhline(CUSUM_H,  color="red",   linestyle="--", linewidth=0.8, label=f"h={CUSUM_H}")
        ax1.axhline(-CUSUM_H, color="green", linestyle="--", linewidth=0.8)
        ax1.set_ylabel("CUSUM")
        ax1.set_xlabel("Điểm thời gian")
        ax1.legend(fontsize=8)
        ax1.grid(alpha=0.3)

        plt.tight_layout()
        out = OUTPUT_PATH / "cusum_drift.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        saved.append(out)
        print(f"[DRIFT] CUSUM → {out.name} (anomalies: {anomalies_cusum.sum()})")
    except Exception as e:
        print(f"[DRIFT] CUSUM lỗi: {e}")

    return saved


# ─────────────────────────────────────────────
# Vẽ đồ thị phân phối (histogram + boxplot)
# ─────────────────────────────────────────────
def plot_distribution(df) -> list[Path]:
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    saved = []
    skip = {"datetime", "date", "time", "sourcefolder", "sourcefile"}
    numeric_cols = [
        c for c in df.columns
        if c.lower() not in skip and pd.api.types.is_numeric_dtype(df[c])
    ][:6]   # tối đa 6 cột

    if not numeric_cols:
        return saved

    n = len(numeric_cols)
    fig, axes = plt.subplots(2, n, figsize=(4 * n, 7))
    if n == 1:
        axes = [[axes[0]], [axes[1]]]
    fig.suptitle("Phân phối dữ liệu — Histogram & Boxplot", fontsize=13, fontweight="bold")

    for i, col in enumerate(numeric_cols):
        data = df[col].dropna()
        ax_hist = axes[0][i] if n > 1 else axes[0][0]
        ax_box  = axes[1][i] if n > 1 else axes[1][0]

        ax_hist.hist(data, bins=30, color="#42A5F5", edgecolor="white", linewidth=0.4)
        ax_hist.set_title(col, fontsize=9)
        ax_hist.set_ylabel("Tần suất" if i == 0 else "")
        ax_hist.grid(alpha=0.3)

        ax_box.boxplot(data, patch_artist=True,
                       boxprops=dict(facecolor="#90CAF9"),
                       medianprops=dict(color="red", linewidth=1.5))
        ax_box.set_xticks([])
        ax_box.grid(alpha=0.3)

    plt.tight_layout()
    out = OUTPUT_PATH / "distribution.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    saved.append(out)
    print(f"[PLOT] Distribution → {out.name}")
    return saved


# ─────────────────────────────────────────────
# Vẽ heatmap tương quan
# ─────────────────────────────────────────────
def plot_correlation(df) -> list[Path]:
    import pandas as pd
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    saved = []
    skip = {"datetime", "date", "time", "sourcefolder", "sourcefile"}
    numeric_df = df[[
        c for c in df.columns
        if c.lower() not in skip and pd.api.types.is_numeric_dtype(df[c])
    ]].dropna()

    if numeric_df.shape[1] < 2:
        return saved

    corr = numeric_df.corr()
    n = len(corr)

    fig, ax = plt.subplots(figsize=(max(6, n), max(5, n - 1)))
    cax = ax.matshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    fig.colorbar(cax)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(corr.columns, rotation=45, ha="left", fontsize=8)
    ax.set_yticklabels(corr.columns, fontsize=8)
    ax.set_title("Ma trận tương quan (Correlation Heatmap)", pad=20, fontsize=12, fontweight="bold")

    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}",
                    ha="center", va="center", fontsize=7,
                    color="black" if abs(corr.iloc[i, j]) < 0.7 else "white")

    plt.tight_layout()
    out = OUTPUT_PATH / "correlation_heatmap.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    saved.append(out)
    print(f"[PLOT] Correlation → {out.name}")
    return saved


# ─────────────────────────────────────────────
# Vẽ line chart theo thời gian
# ─────────────────────────────────────────────
def plot_timeseries(df) -> list[Path]:
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    saved = []
    skip = {"datetime", "date", "time", "sourcefolder", "sourcefile"}

    # Tìm cột thời gian
    time_col = None
    for c in df.columns:
        if c.lower() in {"datetime", "date", "time"}:
            time_col = c
            break

    numeric_cols = [
        c for c in df.columns
        if c.lower() not in skip and pd.api.types.is_numeric_dtype(df[c])
    ][:4]

    if not numeric_cols:
        return saved

    fig, axes = plt.subplots(len(numeric_cols), 1,
                              figsize=(14, 3 * len(numeric_cols)), sharex=True)
    if len(numeric_cols) == 1:
        axes = [axes]
    fig.suptitle("Chuỗi thời gian (Time Series)", fontsize=13, fontweight="bold")

    colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0"]
    for i, col in enumerate(numeric_cols):
        x = df[time_col] if time_col else range(len(df))
        axes[i].plot(x, df[col], linewidth=0.9, color=colors[i % 4])
        axes[i].set_ylabel(col, fontsize=9)
        axes[i].grid(alpha=0.3)

    if time_col:
        axes[-1].set_xlabel(time_col, fontsize=9)
    plt.tight_layout()
    out = OUTPUT_PATH / "timeseries.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    saved.append(out)
    print(f"[PLOT] Timeseries → {out.name}")
    return saved


# ─────────────────────────────────────────────
# Tổng hợp báo cáo
# ─────────────────────────────────────────────
def build_report(import_results: dict, df, all_charts: list[Path]) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    ok  = sum(1 for v in import_results.values() if v.startswith("✅"))
    fail = len(import_results) - ok

    lines = [
        "🤖 <b>ANTIGRAVITY AUTO-DEBUG</b>",
        f"🕐 {now}",
        "",
        f"<b>📦 Kiểm tra module ({ok}/{len(import_results)} OK)</b>",
    ]
    for mod, status in import_results.items():
        lines.append(f"  {status} {mod}")

    if df is not None:
        lines += [
            "",
            "<b>📊 Dữ liệu mẫu</b>",
            f"  Hàng: {len(df):,}",
            f"  Cột : {len(df.columns)} → {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}",
        ]

        # Thống kê nhanh
        import pandas as pd
        skip = {"datetime", "date", "time", "sourcefolder", "sourcefile"}
        num_cols = [c for c in df.columns if c.lower() not in skip
                    and pd.api.types.is_numeric_dtype(df[c])]
        if num_cols:
            lines.append("")
            lines.append("<b>📈 Thống kê cơ bản</b>")
            for c in num_cols[:4]:
                s = df[c].dropna()
                lines.append(
                    f"  <b>{c}</b>: min={s.min():.2f} | mean={s.mean():.2f} "
                    f"| max={s.max():.2f} | NaN={df[c].isna().sum()}"
                )

    lines += [
        "",
        f"<b>🖼️ Đồ thị đã tạo: {len(all_charts)}</b>",
    ]
    for c in all_charts:
        lines.append(f"  • {c.name}")

    status_icon = "✅" if fail == 0 else "⚠️"
    lines += ["", f"{status_icon} Trạng thái: {'Tất cả OK' if fail == 0 else f'{fail} lỗi cần kiểm tra'}"]

    return "\n".join(lines)


# ─────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────
def run_debug():
    print("\n" + "=" * 55)
    print("  ANTIGRAVITY AUTO-DEBUG  —", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print("=" * 55)

    # 1. Kiểm tra import
    print("\n[1/4] Kiểm tra modules...")
    import_results = check_imports()
    for mod, status in import_results.items():
        print(f"  {status} {mod}")

    # 2. Load dữ liệu
    print("\n[2/4] Load dữ liệu mẫu...")
    df = None
    load_error = None
    try:
        df = load_sample_data()
        print(f"  OK → {len(df)} hàng × {len(df.columns)} cột")
    except Exception as e:
        load_error = str(e)
        print(f"  CẢNH BÁO: {e}")

    # 3. Tạo đồ thị
    all_charts: list[Path] = []
    if df is not None:
        print("\n[3/4] Tạo đồ thị...")
        try:
            all_charts += run_drift_and_plot(df)
        except Exception as e:
            print(f"  [DRIFT] Lỗi: {e}\n{traceback.format_exc()}")
        try:
            all_charts += plot_distribution(df)
        except Exception as e:
            print(f"  [DIST] Lỗi: {e}")
        try:
            all_charts += plot_correlation(df)
        except Exception as e:
            print(f"  [CORR] Lỗi: {e}")
        try:
            all_charts += plot_timeseries(df)
        except Exception as e:
            print(f"  [TIME] Lỗi: {e}")
    else:
        print("\n[3/4] Bỏ qua đồ thị (không có dữ liệu)")

    # 4. Gửi Telegram
    print("\n[4/4] Gửi Telegram...")
    report = build_report(import_results, df, all_charts)
    tele_send_text(report)

    for chart in all_charts:
        label = {
            "ewma_drift.png":        "EWMA Drift Detection",
            "cusum_drift.png":       "CUSUM Drift Detection",
            "distribution.png":      "Phân phối dữ liệu (Histogram + Boxplot)",
            "correlation_heatmap.png":"Ma trận tương quan",
            "timeseries.png":        "Chuỗi thời gian",
        }.get(chart.name, chart.name)
        tele_send_photo(chart, caption=f"📊 {label}")
        time.sleep(0.5)   # tránh rate limit Telegram

    print("\nHoàn tất! Đồ thị đã lưu tại:", OUTPUT_PATH)
    return all_charts


# ─────────────────────────────────────────────
# Scheduler
# ─────────────────────────────────────────────
def run_scheduler(interval_minutes: int):
    print(f"[SCHEDULER] Chạy mỗi {interval_minutes} phút. Ctrl+C để dừng.")
    while True:
        try:
            run_debug()
        except Exception as e:
            msg = f"⚠️ ANTIGRAVITY lỗi nghiêm trọng:\n{e}\n{traceback.format_exc()}"
            print(msg)
            tele_send_text(msg)
        print(f"[SCHEDULER] Chờ {interval_minutes} phút...")
        time.sleep(interval_minutes * 60)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antigravity Auto-Debug for Dashboard-VP")
    parser.add_argument(
        "--schedule", type=int, default=0, metavar="PHÚT",
        help="Chạy lập lịch mỗi N phút (0 = chạy 1 lần)"
    )
    args = parser.parse_args()

    if args.schedule > 0:
        run_scheduler(args.schedule)
    else:
        run_debug()
