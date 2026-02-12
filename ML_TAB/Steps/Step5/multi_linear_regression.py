# ML_TAB/Steps/Step5/multi_linear_regression.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


@dataclass
class MultiLRResult:
    metrics_df: pd.DataFrame
    models: Dict[str, Any]
    scaler: StandardScaler
    numeric_cols: List[str]
    n_train: int
    n_test: int


def fit_predict_multilinear_exclude_self(
    df: pd.DataFrame,
    train_idx,
    test_idx,
    alpha: float = 1.0,
    min_rows_train: int = 20,
    min_rows_test: int = 5,
) -> MultiLRResult:
    """
    Multi-Linear Regression kiểu reconstruction (giống AAKR logic):
    - Với từng biến j: input = tất cả numeric cols trừ j, output = col j
    - Train trên train set, predict trên test set
    - Trả về metrics theo từng biến (MAE/RMSE/R2) + scaler + models

    Lưu ý:
    - Drop NaN đồng bộ trên toàn bộ numeric columns để đảm bảo X/y khớp dòng.
    """

    if df is None or df.empty:
        raise ValueError("DataFrame rỗng hoặc None.")

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if len(numeric_cols) < 2:
        raise ValueError("Cần ít nhất 2 cột numeric để chạy MultiLinearRegression (exclude-self).")

    # Lấy đúng rows theo split và dropna đồng bộ
    train_df = df.loc[train_idx, numeric_cols].copy()
    test_df = df.loc[test_idx, numeric_cols].copy()

    train_df = train_df.dropna(subset=numeric_cols)
    test_df = test_df.dropna(subset=numeric_cols)

    n_train = len(train_df)
    n_test = len(test_df)
    if n_train < min_rows_train or n_test < min_rows_test:
        raise ValueError(f"Dữ liệu không đủ sau dropna. Train={n_train}, Test={n_test}")

    # Scale theo train
    scaler = StandardScaler()
    X_train_full = scaler.fit_transform(train_df.values)  # shape: (n_train, p)
    X_test_full = scaler.transform(test_df.values)        # shape: (n_test, p)

    p = len(numeric_cols)
    models: Dict[str, Any] = {}
    rows = []

    # helper: unscale 1 cột (từ scaled -> original)
    mean_ = scaler.mean_
    scale_ = scaler.scale_

    for j, col in enumerate(numeric_cols):
        # Build X_in: loại cột j
        mask = np.ones(p, dtype=bool)
        mask[j] = False

        X_tr = X_train_full[:, mask]
        y_tr = X_train_full[:, j]
        X_te = X_test_full[:, mask]
        y_te_scaled = X_test_full[:, j]

        # Ridge ổn định hơn LinearRegression (giảm nguy cơ "copy")
        model = Ridge(alpha=alpha)
        model.fit(X_tr, y_tr)

        y_pred_scaled = model.predict(X_te)

        # Tính metrics theo đơn vị gốc (original units)
        y_true = test_df[col].values
        y_pred = y_pred_scaled * scale_[j] + mean_[j]

        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        r2 = float(r2_score(y_true, y_pred))

        rows.append((col, mae, rmse, r2))
        models[col] = {
            "model": model,
            "exclude_col": col,
            "input_cols": [c for c in numeric_cols if c != col],
        }

    metrics_df = pd.DataFrame(rows, columns=["Feature", "MAE", "RMSE", "R2"])
    metrics_df = metrics_df.sort_values("RMSE", ascending=False).reset_index(drop=True)

    return MultiLRResult(
        metrics_df=metrics_df,
        models=models,
        scaler=scaler,
        numeric_cols=numeric_cols,
        n_train=n_train,
        n_test=n_test,
    )
