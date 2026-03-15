"""
Debug script: Chạy Forecasting với dữ liệu duchien (không cần GUI)
Đầu ra: forecast_result.png + forecast_result.html
"""
from __future__ import annotations
import sys, warnings
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.optimize import curve_fit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from pathlib import Path

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent

# ─── 1. Load dữ liệu duchien ─────────────────────────────────────────────────
def load_duchien() -> pd.DataFrame:
    """Gộp tất cả CSV trong duchien/ giống như load_data.py làm."""
    dfs = []
    for csv_path in sorted(BASE.glob("duchien/**/*.csv")):
        try:
            df = pd.read_csv(csv_path, dayfirst=True)
            # Chuẩn hoá tên cột
            df.columns = [c.strip() for c in df.columns]
            dfs.append(df)
            print(f"  ✅ Loaded: {csv_path.relative_to(BASE)}  ({len(df):,} rows)")
        except Exception as e:
            print(f"  ⚠️  Skip {csv_path.name}: {e}")

    if not dfs:
        # Thử duchien.csv gốc
        main_csv = BASE / "duchien" / "duchien.csv"
        if main_csv.exists():
            dfs = [pd.read_csv(main_csv, dayfirst=True)]
            print(f"  ✅ Loaded main: duchien.csv  ({len(dfs[0]):,} rows)")

    if not dfs:
        raise FileNotFoundError("Không tìm thấy CSV nào trong duchien/")

    merged = pd.concat(dfs, ignore_index=True)
    return merged


# ─── 2. Chọn target & thực hiện Polynomial Trend ─────────────────────────────
def pick_target(df: pd.DataFrame) -> str:
    TIME_LIKE = {"datetime", "date", "time", "timestamp", "index", "unnamed"}
    numeric_cols = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and c.lower().strip() not in TIME_LIKE
    ]

    # Ưu tiên cột có 'DP' hoặc 'dp' (differential pressure - suy giảm đặc trưng)
    for c in numeric_cols:
        if "dp" in c.lower():
            return c
    # Không thấy DP → dùng cột numeric đầu tiên có std > 0
    for c in numeric_cols:
        if df[c].std() > 0:
            return c
    return numeric_cols[0]


def run_poly_forecast(df: pd.DataFrame, target: str,
                      poly_degree: int = 2,
                      horizon: int = 720,
                      wash_threshold: float = -4.0,
                      mw_col: str = "",
                      mw_min: float = 0.0):

    cols_needed = [c for c in [target, mw_col] if c and c in df.columns]
    df_work = df[cols_needed].dropna().reset_index(drop=True)

    # Lọc MW
    if mw_col and mw_col in df_work.columns and mw_min > 0:
        before = len(df_work)
        df_work = df_work[df_work[mw_col] >= mw_min].reset_index(drop=True)
        print(f"  Lọc MW≥{mw_min}: bỏ {before - len(df_work):,} pts, còn {len(df_work):,} pts")

    y_all = df_work[target].values.astype(float)
    x_all = np.arange(len(y_all), dtype=float)

    ratio  = 0.8
    n_train = max(10, int(len(y_all) * ratio))
    x_train, y_train = x_all[:n_train], y_all[:n_train]
    x_test,  y_test  = x_all[n_train:], y_all[n_train:]

    # Fit polynomial
    coeffs     = np.polyfit(x_train, y_train, deg=poly_degree)
    predict_fn = lambda x: np.polyval(coeffs, x)

    y_train_pred = predict_fn(x_train)
    y_test_pred  = predict_fn(x_test) if len(x_test) > 0 else np.array([])

    # Metrics
    mae = rmse = r2 = mape = None
    if len(y_test) > 0:
        mae  = float(mean_absolute_error(y_test, y_test_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_test_pred)))
        r2   = float(r2_score(y_test, y_test_pred))
        nz   = y_test != 0
        if nz.sum() > 0:
            mape = float(np.mean(np.abs((y_test[nz] - y_test_pred[nz]) / y_test[nz])) * 100)

    # Future forecast
    going_down = wash_threshold < y_all[-1]
    future_x   = np.arange(x_all[-1] + 1, x_all[-1] + 1 + horizon)
    future_pred = predict_fn(future_x)
    wash_step   = None
    for i, v in enumerate(future_pred):
        if going_down and v <= wash_threshold:
            wash_step = i
            break
        elif not going_down and v >= wash_threshold:
            wash_step = i
            break

    return dict(
        x_all=x_all, y_all=y_all,
        x_train=x_train, y_train_pred=y_train_pred,
        x_test=x_test,  y_test_pred=y_test_pred,
        future_x=future_x, future_pred=future_pred,
        n_train=n_train, n_test=len(y_test),
        mae=mae, rmse=rmse, r2=r2, mape=mape,
        wash_step=wash_step, wash_threshold=wash_threshold,
        poly_degree=poly_degree,
    )


# ─── 3. Vẽ đồ thị Plotly ─────────────────────────────────────────────────────
def plot_result(res: dict, target: str) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("📈 Forecast — Dự báo suy giảm", "🔍 Train / Test Fit"),
        vertical_spacing=0.12,
    )
    x_all       = res["x_all"]
    y_all       = res["y_all"]
    x_train     = res["x_train"]
    future_x    = res["future_x"]
    future_pred = res["future_pred"]
    wash_step   = res["wash_step"]
    wash_thr    = res["wash_threshold"]
    deg         = res["poly_degree"]

    # — ROW 1: Forecast ———————————————————————————————————————————————————————
    # Dữ liệu thực
    fig.add_trace(go.Scatter(
        x=x_all, y=y_all,
        mode="lines", name="Actual data",
        line=dict(color="#42a5f5", width=1),
    ), row=1, col=1)

    # Trend fit trên lịch sử
    from numpy.polynomial import polynomial as P
    coeffs     = np.polyfit(x_train, res["y_train_pred"], deg=0) # dummy - dùng lại pred
    fit_x      = np.concatenate([x_train, res["x_test"]]) if len(res["x_test"]) > 0 else x_train
    fit_y      = np.concatenate([res["y_train_pred"], res["y_test_pred"]]) if len(res["x_test"]) > 0 else res["y_train_pred"]

    fig.add_trace(go.Scatter(
        x=fit_x, y=fit_y,
        mode="lines", name=f"Poly Trend (deg={deg})",
        line=dict(color="#ffb300", width=2, dash="dot"),
    ), row=1, col=1)

    # Future forecast
    fig.add_trace(go.Scatter(
        x=future_x, y=future_pred,
        mode="lines", name="Forecast",
        line=dict(color="#ef5350", width=2),
    ), row=1, col=1)

    # Wash threshold line
    all_x = np.concatenate([x_all, future_x])
    fig.add_trace(go.Scatter(
        x=[all_x[0], all_x[-1]],
        y=[wash_thr, wash_thr],
        mode="lines", name=f"Wash threshold ({wash_thr})",
        line=dict(color="#e040fb", width=1.5, dash="dash"),
    ), row=1, col=1)

    # Wash marker
    if wash_step is not None:
        wx = future_x[wash_step]
        wy = future_pred[wash_step]
        fig.add_trace(go.Scatter(
            x=[wx], y=[wy],
            mode="markers+text",
            marker=dict(color="#e040fb", size=12, symbol="x"),
            text=[f"⚠️ Wash in {wash_step} steps"],
            textposition="top center",
            name=f"Wash Point (step {wash_step})",
        ), row=1, col=1)

    # Train/test split line
    fig.add_vline(x=float(x_train[-1]), line_dash="dash",
                  line_color="gray", row=1, col=1)
    fig.add_annotation(x=float(x_train[-1]), y=y_all.max(),
                       text="Train|Test", showarrow=False,
                       font=dict(color="gray", size=10), row=1, col=1)

    # — ROW 2: Train/Test Fit —————————————————————————————————————————————————
    fig.add_trace(go.Scatter(
        x=x_train, y=y_all[:len(x_train)],
        mode="lines", name="Train actual",
        line=dict(color="#42a5f5", width=1), showlegend=False,
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=x_train, y=res["y_train_pred"],
        mode="lines", name="Train fit",
        line=dict(color="#ffb300", width=2, dash="dot"), showlegend=False,
    ), row=2, col=1)

    if len(res["x_test"]) > 0:
        fig.add_trace(go.Scatter(
            x=res["x_test"], y=y_all[len(x_train):],
            mode="lines", name="Test actual",
            line=dict(color="#81d4fa", width=1), showlegend=False,
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=res["x_test"], y=res["y_test_pred"],
            mode="lines", name="Test pred",
            line=dict(color="#ef5350", width=2, dash="dot"), showlegend=False,
        ), row=2, col=1)

    # Metrics annotation
    mae  = res["mae"]
    rmse = res["rmse"]
    r2   = res["r2"]
    mape = res["mape"]
    metrics_text = (
        f"MAE={mae:.4f}  RMSE={rmse:.4f}  R²={r2:.4f}  MAPE={mape:.2f}%"
        if mae is not None else "No test data"
    )
    wash_text = (
        f"🚿 Cần vệ sinh sau <b>{wash_step} steps</b>"
        if wash_step is not None else "✅ Chưa đạt ngưỡng vệ sinh trong forecast horizon"
    )

    fig.update_layout(
        title=dict(
            text=(
                f"<b>Degradation Forecasting — {target}</b><br>"
                f"<sup>Polynomial Trend deg={deg}  |  {metrics_text}</sup><br>"
                f"<sup>{wash_text}</sup>"
            ),
            font=dict(size=15),
        ),
        template="plotly_dark",
        height=800,
        legend=dict(orientation="h", y=-0.08),
    )
    fig.update_xaxes(title_text="Step (data point index)")
    fig.update_yaxes(title_text=target)

    return fig


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  DEBUG: Forecasting — duchien data")
    print("=" * 60)

    # 1. Load
    print("\n[1] Loading data...")
    df = load_duchien()
    print(f"  Merged: {df.shape[0]:,} rows × {df.shape[1]} cols")
    print(f"  Columns: {list(df.columns)}")

    # 2. Pick target
    target = pick_target(df)
    print(f"\n[2] Target selected: {target}")

    # Tự động tìm cột MW nếu có
    mw_col = ""
    for c in df.columns:
        if "mw" in c.lower() or "net" in c.lower():
            mw_col = c
            break
    print(f"  MW col: {mw_col if mw_col else '(None)'}")

    # 3. Run forecasting
    print(f"\n[3] Running Polynomial Trend (deg=2)...")
    res = run_poly_forecast(
        df, target=target,
        poly_degree=2,
        horizon=720,
        wash_threshold=-4.0,
        mw_col=mw_col,
        mw_min=0.0,  # không lọc MW nếu ko có cột MW rõ ràng
    )

    mae  = res["mae"]
    rmse = res["rmse"]
    r2   = res["r2"]
    mape = res["mape"]
    ws   = res["wash_step"]
    print(f"\n[4] Results:")
    print(f"  Train pts   : {res['n_train']:,}")
    print(f"  Test pts    : {res['n_test']:,}")
    print(f"  MAE         : {mae:.4f}"  if mae  is not None else "  MAE: N/A")
    print(f"  RMSE        : {rmse:.4f}" if rmse is not None else "  RMSE: N/A")
    print(f"  R²          : {r2:.4f}"   if r2   is not None else "  R²: N/A")
    print(f"  MAPE        : {mape:.2f}%" if mape is not None else "  MAPE: N/A")
    print(f"  Wash step   : {ws} steps" if ws is not None else "  Wash: Chưa đạt ngưỡng")

    # 4. Vẽ và lưu
    print(f"\n[5] Generating chart...")
    fig = plot_result(res, target)

    # Lưu PNG
    out_png  = BASE / "logs" / "forecast_result.png"
    out_html = BASE / "logs" / "forecast_result.html"
    out_png.parent.mkdir(exist_ok=True)

    try:
        fig.write_image(str(out_png), width=1400, height=850, scale=2)
        print(f"  ✅ Saved PNG : {out_png}")
    except Exception as e:
        print(f"  ⚠️  PNG failed ({e}) — saving HTML instead")

    import plotly.io as pio
    pio.write_html(fig, str(out_html), full_html=True, include_plotlyjs=True, auto_open=False)
    print(f"  ✅ Saved HTML: {out_html}")

    print("\n✅ Done!")
