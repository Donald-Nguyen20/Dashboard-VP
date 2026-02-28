from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
@dataclass
class RecentTrendHit:
    tag: str
    start: pd.Timestamp
    end: pd.Timestamp
    direction: str   # "UP" / "DOWN"
    months: int
    strength: float  # slope_ratio

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

def detect_recent_trend_longest_months(
    s: pd.Series,
    tag: str,
    min_months: int = 3,
    max_months: int = 12,
    resample_rule: str = "1D",
    slope_ratio_thr: float = 0.18,
) -> Optional[RecentTrendHit]:
    """
    Tìm xu hướng "gần nhất" (đoạn kết thúc tại end của data) có độ dài LỚN NHẤT (>= min_months).
    - Nếu 5 tháng đạt ngưỡng -> báo 5 tháng (không báo 4/3).
    - Nếu chỉ 3 tháng gần nhất đạt -> báo 3 tháng.
    """

    x = _to_num(s).dropna()

    # cần DatetimeIndex để cắt theo tháng
    if not isinstance(x.index, pd.DatetimeIndex) or x.size < 120:
        return None

    # resample để giảm nhiễu
    xr = x.resample(resample_rule).median().dropna()
    if xr.size < 60:
        return None

    end = xr.index.max()

    # duyệt từ lớn -> nhỏ để lấy "months lớn nhất"
    for m in range(max_months, min_months - 1, -1):
        start = end - pd.DateOffset(months=m)
        seg = xr[xr.index >= start]
        # ✅ bắt buộc dữ liệu phải phủ đủ m tháng (cho phép lệch 2 ngày)
        if seg.empty:
            continue
        if seg.index.min() > (start + pd.Timedelta(days=2)):
            continue

        if seg.size < max(45, m * 20):  # tối thiểu số điểm để tin cậy
            continue

        y = seg.to_numpy(dtype=float)
        slope = _linear_slope(y)
        span = float(len(y) - 1)

        med = float(np.median(y))
        base = abs(med) if abs(med) > 1e-12 else float(np.std(y) + 1.0)

        ratio = abs(slope) * span / base

        if ratio >= slope_ratio_thr:
            direction = "UP" if slope > 0 else "DOWN"

            rd = relativedelta(end.to_pydatetime(), seg.index.min().to_pydatetime())
            months_actual = rd.years * 12 + rd.months

            if months_actual < min_months:
                continue

            return RecentTrendHit(
                tag=tag,
                start=seg.index.min(),
                end=seg.index.max(),
                direction=direction,
                months=months_actual,  
                strength=float(ratio),
            )

    return None