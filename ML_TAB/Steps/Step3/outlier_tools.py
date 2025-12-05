# ML_TAB/Steps/Step3/outlier_tools.py
from __future__ import annotations
import re
import numpy as np
import pandas as pd
from typing import Optional, List, Tuple, Dict, Any

from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

# Thêm đoạn này

from pyod.models.ecod import ECOD
from pyod.models.copod import COPOD
from pyod.models.knn import KNN

# ---------- utils ----------
def _infer_timestamp_col(df: pd.DataFrame, user_col: Optional[str] = None) -> Optional[str]:
    if user_col and user_col in df.columns:
        return user_col
    # ưu tiên dtype datetime
    for c in df.columns:
        if np.issubdtype(df[c].dtype, np.datetime64):
            return c
    # fallback theo tên
    pat = re.compile(r"(time|date|timestamp|datetime)", re.I)
    for c in df.columns:
        if pat.search(str(c)):
            return c
    return None

def _numeric_columns(df: pd.DataFrame, prefer: Optional[List[str]] = None) -> List[str]:
    if prefer:
        return [c for c in prefer if c in df.columns]
    return df.select_dtypes(include=[np.number]).columns.tolist()

def _mk_result_df(
    rows: List[Tuple[int, Optional[object], str, object, float, str]]
) -> pd.DataFrame:
    # rows: (row_index, timestamp, column, value, score, method)
    if not rows:
        return pd.DataFrame(columns=["row_index","timestamp","column","value","score","method"])
    return pd.DataFrame(rows, columns=["row_index","timestamp","column","value","score","method"])

# ---------- Detector 1: IQR (điểm/column-level) ----------
def detect_outliers_iqr(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    factor: float = 1.5,
    timestamp_col: Optional[str] = None,
) -> pd.DataFrame:
    cols = _numeric_columns(df, columns)
    ts_col = _infer_timestamp_col(df, timestamp_col)
    rows: List[Tuple[int, Optional[object], str, object, float, str]] = []

    for col in cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr):
            continue
        lower = q1 if iqr == 0 else q1 - factor * iqr
        upper = q3 if iqr == 0 else q3 + factor * iqr
        mask = (df[col] < lower) | (df[col] > upper)
        if mask.any():
            for idx in df.index[mask]:
                ts = df.loc[idx, ts_col] if (ts_col and ts_col in df.columns) else None
                val = df.loc[idx, col]
                # score = độ lệch biên (xa biên -> lớn hơn)
                if val < lower:
                    score = float(lower - val)
                elif val > upper:
                    score = float(val - upper)
                else:
                    score = 0.0
                rows.append((int(idx), ts, col, val, score, "IQR"))
    return _mk_result_df(rows)

# ---------- Detector 2: Z-score (điểm/column-level) ----------
def detect_outliers_zscore(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    z: float = 3.0,
    timestamp_col: Optional[str] = None,
    ddof: int = 0,
) -> pd.DataFrame:
    cols = _numeric_columns(df, columns)
    ts_col = _infer_timestamp_col(df, timestamp_col)
    rows: List[Tuple[int, Optional[object], str, object, float, str]] = []

    for col in cols:
        series = df[col].astype(float)
        mu, sigma = series.mean(), series.std(ddof=ddof)
        if sigma == 0 or np.isnan(sigma):
            continue
        zscores = (series - mu) / sigma
        mask = zscores.abs() > z
        if mask.any():
            for idx in df.index[mask]:
                ts = df.loc[idx, ts_col] if (ts_col and ts_col in df.columns) else None
                val = df.loc[idx, col]
                score = float(zscores.loc[idx])
                rows.append((int(idx), ts, col, val, score, "Z-SCORE"))
    return _mk_result_df(rows)

# ---------- Detector: Modified Z-score (column-level) ----------
def detect_outliers_modified_zscore(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    threshold: float = 3.5,
    timestamp_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Modified Z-score dùng median + MAD, robust hơn Z-score thường.
    Trả về DF:
        row_index | timestamp | column | value | score | method = "MOD_Z"
    """
    cols = _numeric_columns(df, columns)
    if not cols:
        return _mk_result_df([])

    ts_col = _infer_timestamp_col(df, timestamp_col)
    rows: List[Tuple[int, Optional[object], str, object, float, str]] = []

    for col in cols:
        series = df[col].astype(float)

        median = series.median()
        mad = (series - median).abs().median()
        if mad == 0 or np.isnan(mad):
            # không tính được, bỏ qua cột
            continue

        # Modified Z-score
        mz = 0.6745 * (series - median) / (mad + 1e-9)
        mz_abs = mz.abs()
        mask = mz_abs > threshold

        for idx in series[mask].index:
            ts = (
                df.loc[idx, ts_col]
                if ts_col and ts_col in df.columns
                else None
            )
            val = df.loc[idx, col]
            score = float(mz_abs.loc[idx])
            rows.append((int(idx), ts, col, val, score, "MOD_Z"))

    return _mk_result_df(rows)

# ---------- Detector 3: IsolationForest (hàng/row-level) ----------
def detect_outliers_isoforest(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    contamination: float = 0.05,
    random_state: int = 42,
    timestamp_col: Optional[str] = None,
    n_estimators: int = 200,
    topk: int = 3,                  # NEW: số biến giải thích
    return_json: bool = True        # NEW: thêm cột causes_json
) -> pd.DataFrame:
    """
    Phát hiện outlier bằng IsolationForest và giải thích đa-biến bằng robust-z (top-k).
    Trả về DataFrame có các cột:
    row_index | timestamp | column | value | score | method | causes | (optional) causes_json
    """
    cols = _numeric_columns(df, columns)
    if not cols:
        return _mk_result_df([])

    ts_col = _infer_timestamp_col(df, timestamp_col)
    X = df[cols].astype(float)

    iso = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=n_estimators,
        n_jobs=-1
    )
    pred = iso.fit_predict(X)            # 1 bình thường, -1 outlier
    scores = iso.decision_function(X)    # càng nhỏ càng bất thường

    # --- robust center & scale cho giải thích ---
    med = X.median(axis=0)
    mad = (X - med).abs().median(axis=0)
    eps = 1e-9
    scale = 1.4826 * mad + eps

    rows: List[Tuple[int, Optional[object], str, object, float, str]] = []
    causes_col: List[str] = []
    causes_json_col: List[List[Dict[str, Any]]] = []

    mask = (pred == -1)
    if mask.any():
        for idx in df.index[mask]:
            ts = df.loc[idx, ts_col] if (ts_col and ts_col in df.columns) else None
            i = df.index.get_loc(idx)

            # robust-z từng biến cho dòng outlier
            x = X.loc[idx, cols]
            rz = ((x - med) / scale).abs()
            rz = rz.replace([np.inf, -np.inf], np.nan).fillna(0.0)

            # chọn top-k biến
            top = rz.nlargest(max(1, topk))
            causes_list = []
            for feat in top.index:
                causes_list.append({
                    "feature": feat,
                    "value": float(x[feat]),
                    "robust_z": float(top[feat])
                })

            # chuỗi gọn cho hiển thị
            causes_str = ", ".join(
                f"{c['feature']}={c['value']:.6g} (|rz|={c['robust_z']:.2f})"
                for c in causes_list
            )

            rows.append((int(idx), ts, "<row>", None, float(scores[i]), "ISOFOR"))
            causes_col.append(causes_str)
            causes_json_col.append(causes_list)

    out = _mk_result_df(rows)
    if not out.empty:
        out = out.reset_index(drop=True)
        out["causes"] = causes_col
        if return_json:
            out["causes_json"] = causes_json_col
    return out

# ---------- Detector 4: LOF ----------
def detect_outliers_lof(
    df,
    columns=None,
    n_neighbors=20,
    contamination=0.05,
    timestamp_col=None
):
    cols = columns or df.select_dtypes(include='number').columns
    if not len(cols):
        return pd.DataFrame(columns=["row_index","timestamp","column","value","score","method"])

    ts_col = _infer_timestamp_col(df, timestamp_col)
    X = df[cols].astype(float)
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    pred = lof.fit_predict(X)   # -1 là outlier
    scores = lof.negative_outlier_factor_

    rows = []
    for idx, label in zip(df.index, pred):
        if label == -1:  # chỉ lấy outlier
            ts = df.loc[idx, ts_col] if ts_col and ts_col in df.columns else None
            score = float(scores[df.index.get_loc(idx)])
            rows.append((int(idx), ts, "<row>", None, score, "LOF"))
    return _mk_result_df(rows)

def combine_outlier_results(
    df_iqr: pd.DataFrame,
    df_z: pd.DataFrame,
    how: str = "intersection"
) -> pd.DataFrame:
    """
    Kết hợp kết quả giữa hai phương pháp outlier (IQR & Z-score).

    - how = 'intersection':
        GIAO chuẩn theo (row_index, column):
        Chỉ giữ những ô (row_index, column) cùng bị gắn cờ
        ở cả IQR lẫn Z-score.

    - how = 'union':
        HỢP theo (row_index, column):
        Giữ những ô bị gắn cờ bởi IQR HOẶC Z-score (hoặc cả hai).
    """
    # Cả 2 đều rỗng -> trả về DataFrame rỗng với đúng schema
    if df_iqr.empty and df_z.empty:
        return pd.DataFrame(columns=df_iqr.columns)

    key = ["row_index", "column"]

    if how == "intersection":
        # Nếu 1 trong 2 rỗng thì giao chuẩn = rỗng
        if df_iqr.empty or df_z.empty:
            return pd.DataFrame(columns=df_iqr.columns)

        # GIAO chuẩn theo (row_index, column):
        # chỉ giữ các ô xuất hiện trong cả df_iqr và df_z
        df_comb = df_iqr.merge(
            df_z[key].drop_duplicates(),
            on=key,
            how="inner",
        )
        if df_comb.empty:
            return pd.DataFrame(columns=df_iqr.columns)

        # Đảm bảo cột & thứ tự giống df_iqr, đổi method + source
        df_comb = df_comb[df_iqr.columns]
        df_comb["method"] = "IQR + Z-Score"
        df_comb["source"] = "IQR ∩ Z-score"

    elif how == "union":
        # HỢP theo (row_index, column): gộp cả 2, bỏ trùng ô
        both = pd.concat([df_iqr, df_z], ignore_index=True)
        if both.empty:
            return pd.DataFrame(columns=df_iqr.columns)

        both = both.drop_duplicates(subset=key)
        df_comb = both.copy()
        df_comb["source"] = "IQR ∪ Z-score"
    else:
        raise ValueError("how must be 'intersection' or 'union'")

    return df_comb

# ---------- Detector: ECOD (row-level) ----------
def detect_outliers_ecod(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    contamination: float = 0.05,
    timestamp_col: Optional[str] = None,
    topk: int = 3,
    return_json: bool = True,
) -> pd.DataFrame:
    """
    ECOD (Energy-based Outlier Detection) từ PyOD.
    + Hoạt động theo row-level giống IsolationForest.
    + Giải thích top-k feature đẩy row thành outlier bằng robust-z.
    """

    cols = _numeric_columns(df, columns)
    if not cols:
        return _mk_result_df([])

    ts_col = _infer_timestamp_col(df, timestamp_col)
    X = df[cols].astype(float)

    model = ECOD(contamination=contamination)
    model.fit(X)

    labels = model.labels_           # 1 = outlier, 0 = normal
    scores = model.decision_scores_  # càng lớn càng bất thường

    # robust center + scale cho giải thích
    med = X.median(axis=0)
    mad = (X - med).abs().median(axis=0)
    eps = 1e-9
    scale = 1.4826 * mad + eps

    rows: List[Tuple[int, Optional[object], str, object, float, str]] = []
    causes_col: List[str] = []
    causes_json_col: List[List[Dict[str, Any]]] = []

    for idx, label in zip(df.index, labels):
        if label != 1:
            continue

        ts = df.loc[idx, ts_col] if ts_col and ts_col in df.columns else None
        i = df.index.get_loc(idx)

        x = X.loc[idx, cols]
        rz = ((x - med) / scale).abs()
        rz = rz.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        top = rz.nlargest(max(1, topk))
        causes_list: List[Dict[str, Any]] = []
        for feat in top.index:
            causes_list.append(
                {
                    "feature": feat,
                    "value": float(x[feat]),
                    "robust_z": float(top[feat]),
                }
            )

        causes_str = ", ".join(
            f"{c['feature']}={c['value']:.6g} (|rz|={c['robust_z']:.2f})"
            for c in causes_list
        )

        rows.append((int(idx), ts, "<row>", None, float(scores[i]), "ECOD"))
        causes_col.append(causes_str)
        causes_json_col.append(causes_list)

    out = _mk_result_df(rows)
    if not out.empty:
        out = out.reset_index(drop=True)
        out["causes"] = causes_col
        if return_json:
            out["causes_json"] = causes_json_col
    return out


# ---------- Detector: COPOD (row-level) ----------
def detect_outliers_copod(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    contamination: float = 0.05,
    timestamp_col: Optional[str] = None,
    topk: int = 3,
    return_json: bool = True,
) -> pd.DataFrame:
    """
    COPOD (Copula-based Outlier Detection) từ PyOD.
    Cũng row-level + giải thích top-k feature giống ECOD.
    """


    cols = _numeric_columns(df, columns)
    if not cols:
        return _mk_result_df([])

    ts_col = _infer_timestamp_col(df, timestamp_col)
    X = df[cols].astype(float)

    model = COPOD(contamination=contamination)
    model.fit(X)

    labels = model.labels_
    scores = model.decision_scores_

    med = X.median(axis=0)
    mad = (X - med).abs().median(axis=0)
    eps = 1e-9
    scale = 1.4826 * mad + eps

    rows: List[Tuple[int, Optional[object], str, object, float, str]] = []
    causes_col: List[str] = []
    causes_json_col: List[List[Dict[str, Any]]] = []

    for idx, label in zip(df.index, labels):
        if label != 1:
            continue

        ts = df.loc[idx, ts_col] if ts_col and ts_col in df.columns else None
        i = df.index.get_loc(idx)

        x = X.loc[idx, cols]
        rz = ((x - med) / scale).abs()
        rz = rz.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        top = rz.nlargest(max(1, topk))
        causes_list: List[Dict[str, Any]] = []
        for feat in top.index:
            causes_list.append(
                {
                    "feature": feat,
                    "value": float(x[feat]),
                    "robust_z": float(top[feat]),
                }
            )

        causes_str = ", ".join(
            f"{c['feature']}={c['value']:.6g} (|rz|={c['robust_z']:.2f})"
            for c in causes_list
        )

        rows.append((int(idx), ts, "<row>", None, float(scores[i]), "COPOD"))
        causes_col.append(causes_str)
        causes_json_col.append(causes_list)

    out = _mk_result_df(rows)
    if not out.empty:
        out = out.reset_index(drop=True)
        out["causes"] = causes_col
        if return_json:
            out["causes_json"] = causes_json_col
    return out


# ---------- Detector: KNN (row-level) ----------
def detect_outliers_knn(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    n_neighbors: int = 20,
    contamination: float = 0.05,
    timestamp_col: Optional[str] = None,
    topk: int = 3,
    return_json: bool = True,
) -> pd.DataFrame:
    """
    KNN detector từ PyOD (distance-based).
    Row-level + giải thích feature giống ECOD/COPOD.
    """


    cols = _numeric_columns(df, columns)
    if not cols:
        return _mk_result_df([])

    ts_col = _infer_timestamp_col(df, timestamp_col)
    X = df[cols].astype(float)

    model = KNN(
        n_neighbors=n_neighbors,
        contamination=contamination,
    )
    model.fit(X)

    labels = model.labels_
    scores = model.decision_scores_

    med = X.median(axis=0)
    mad = (X - med).abs().median(axis=0)
    eps = 1e-9
    scale = 1.4826 * mad + eps

    rows: List[Tuple[int, Optional[object], str, object, float, str]] = []
    causes_col: List[str] = []
    causes_json_col: List[List[Dict[str, Any]]] = []

    for idx, label in zip(df.index, labels):
        if label != 1:
            continue

        ts = df.loc[idx, ts_col] if ts_col and ts_col in df.columns else None
        i = df.index.get_loc(idx)

        x = X.loc[idx, cols]
        rz = ((x - med) / scale).abs()
        rz = rz.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        top = rz.nlargest(max(1, topk))
        causes_list: List[Dict[str, Any]] = []
        for feat in top.index:
            causes_list.append(
                {
                    "feature": feat,
                    "value": float(x[feat]),
                    "robust_z": float(top[feat]),
                }
            )

        causes_str = ", ".join(
            f"{c['feature']}={c['value']:.6g} (|rz|={c['robust_z']:.2f})"
            for c in causes_list
        )

        rows.append((int(idx), ts, "<row>", None, float(scores[i]), "KNN"))
        causes_col.append(causes_str)
        causes_json_col.append(causes_list)

    out = _mk_result_df(rows)
    if not out.empty:
        out = out.reset_index(drop=True)
        out["causes"] = causes_col
        if return_json:
            out["causes_json"] = causes_json_col
    return out
