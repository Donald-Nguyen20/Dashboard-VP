from __future__ import annotations
from typing import List
import numpy as np
import pandas as pd
from .types import TrendEvent

def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")

def _linear_slope(y: np.ndarray) -> float:
    t = np.arange(len(y), dtype=float)
    t_mean = t.mean()
    y_mean = y.mean()
    denom = ((t - t_mean) ** 2).sum()
    if denom <= 0:
        return 0.0
    return float(((t - t_mean) * (y - y_mean)).sum() / denom)

def _resample_series(s: pd.Series, rule: str) -> pd.Series:
    if isinstance(s.index, pd.DatetimeIndex):
        return s.resample(rule).median().dropna()
    return s.dropna()

def detect_trend_extremes(
    s: pd.Series,
    tag: str,
    span_desc: str,
    resample_rule: str = "1D",
    slope_ratio_thr: float = 0.15,
) -> List[TrendEvent]:
    x = _to_num(s).dropna()
    if x.size < 60:
        return []

    xr = _resample_series(x, resample_rule)
    if xr.size < 12:
        return []

    y = xr.to_numpy(dtype=float)
    slope = _linear_slope(y)
    span = float(len(y) - 1)

    med = float(np.median(y))
    base = abs(med) if abs(med) > 1e-12 else float(np.std(y) + 1.0)
    ratio = abs(slope) * span / base

    if ratio < slope_ratio_thr:
        return []

    kind = "UP" if slope > 0 else "DOWN"
    return [TrendEvent(tag=tag, kind=kind, span_desc=span_desc, slope_ratio=float(ratio))]

def detect_trend_max_min_6m(
    s: pd.Series,
    tag: str,
    span_desc: str = "6 tháng",
    slope_ratio_thr: float = 0.15,
) -> List[TrendEvent]:
    x = _to_num(s).dropna()
    if x.size < 120 or not isinstance(x.index, pd.DatetimeIndex):
        return []

    wk_max = x.resample("1W").max().dropna()
    wk_min = x.resample("1W").min().dropna()

    out: List[TrendEvent] = []

    if wk_max.size >= 12:
        y = wk_max.to_numpy(dtype=float)
        slope = _linear_slope(y)
        span = float(len(y) - 1)
        base = abs(np.median(y)) if abs(np.median(y)) > 1e-12 else float(np.std(y) + 1.0)
        ratio = abs(slope) * span / base
        if slope > 0 and ratio >= slope_ratio_thr:
            out.append(TrendEvent(tag=tag, kind="MAX_UP", span_desc=span_desc, slope_ratio=float(ratio)))

    if wk_min.size >= 12:
        y = wk_min.to_numpy(dtype=float)
        slope = _linear_slope(y)
        span = float(len(y) - 1)
        base = abs(np.median(y)) if abs(np.median(y)) > 1e-12 else float(np.std(y) + 1.0)
        ratio = abs(slope) * span / base
        if slope < 0 and ratio >= slope_ratio_thr:
            out.append(TrendEvent(tag=tag, kind="MIN_DOWN", span_desc=span_desc, slope_ratio=float(ratio)))

    return out