from __future__ import annotations
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd
from .types import OscillationEvent

def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")

def _fmt_ts(t) -> str:
    try:
        if isinstance(t, pd.Timestamp):
            return t.strftime("%Y-%m-%d %H:%M:%S")
        return str(t)
    except Exception:
        return str(t)

def _rolling_median(x: pd.Series, w: int) -> pd.Series:
    mp = min(w, max(2, w // 3))  # luôn <= w, và tối thiểu 2
    return x.rolling(window=w, min_periods=mp, center=True).median()
def _infer_step_minutes(idx) -> float:
    # median khoảng cách thời gian giữa các điểm (phút)
    try:
        if isinstance(idx, pd.DatetimeIndex) and len(idx) >= 3:
            dt = idx.to_series().diff().dt.total_seconds().median()
            if dt and np.isfinite(dt) and dt > 0:
                return float(dt / 60.0)
    except Exception:
        pass
    return 1.0  # fallback (coi như 1 phút/điểm)

def _points_for_minutes(idx, minutes: float, min_points: int = 3) -> int:
    step = _infer_step_minutes(idx)
    pts = int(np.ceil(minutes / step))
    return max(min_points, pts)
def _count_flips(x: pd.Series) -> int:
    d = x.diff().dropna()
    if d.size < 4:   # ✅ cho phép ít điểm hơn
        return 0
    sign = np.sign(d.to_numpy())
    return int(np.sum((sign[1:] * sign[:-1]) < 0))

def _stable_mw_segments(
    mw: pd.Series,
    min_minutes: int,
    std_thr_ratio: float = 0.03, # MW ổn định nếu độ lệch chuẩn trong cửa sổ w nhỏ hơn 3% của base (base có thể là độ lệch chuẩn toàn bộ hoặc giá trị tuyệt đối trung vị)
    slope_thr_ratio: float = 0.003,
) -> List[Tuple[int, int]]:
    x = _to_num(mw)

    # số điểm tối thiểu để xét MW ổn định (theo thời gian thật)
    w = _points_for_minutes(x.index, float(min_minutes), min_points=4)  # ví dụ 2h với 15 phút/điểm => 8 điểm
    if x.dropna().size < w:
        return []

    mw_med = float(np.median(x.dropna().to_numpy()))
    base = abs(mw_med) if abs(mw_med) > 1e-9 else float(x.dropna().std() + 1.0)

    roll_std = x.rolling(w, min_periods=max(3, w // 2)).std()
    roll_med = _rolling_median(x, w)

    # ✅ chuẩn hoá slope theo "mỗi giờ" để không phụ thuộc 1 điểm = 1 phút hay 15 phút
    step_min = _infer_step_minutes(x.index)
    roll_slope = roll_med.diff().abs() * (60.0 / step_min)

    stable = ((roll_std / base) < std_thr_ratio) & ((roll_slope / base) < slope_thr_ratio)
    stable = stable.fillna(False).to_numpy()

    segs: List[Tuple[int, int]] = []
    i, n = 0, len(stable)
    while i < n:
        if not stable[i]:
            i += 1
            continue
        j = i
        while j < n and stable[j]:
            j += 1
        if (j - i) >= w:
            segs.append((i, j))
        i = j
    return segs

def detect_oscillation_when_mw_stable(
    tag_s: pd.Series,
    tag: str,
    mw_s: Optional[pd.Series],
    min_hours: int = 2,
    std_ratio_thr: float = 2.0,
    flips_thr: int = 6,
) -> List[OscillationEvent]:
    x = _to_num(tag_s)

    # đủ dữ liệu tối thiểu để tính toán
    min_total_points = _points_for_minutes(x.index, minutes=4 * 60, min_points=12)
    if x.dropna().size < min_total_points:
        return []

    # nếu không có MW thì fallback: chỉ dựa flips trên toàn chuỗi
    if mw_s is None:
        flips = _count_flips(x.dropna())
        if flips >= flips_thr:
            return [OscillationEvent(tag, _fmt_ts(x.index.min()), _fmt_ts(x.index.max()), 1.0, flips, None)]
        return []

    mwx = _to_num(mw_s)

    # 1) tìm các đoạn MW ổn định
    segs = _stable_mw_segments(mwx, min_minutes=min_hours * 60)
    if not segs:
        return []

    # 2) base_std chỉ tính trên các điểm thuộc MW ổn định
    stable_series_list = [x.iloc[i:j] for (i, j) in segs]
    base_series = pd.concat(stable_series_list).dropna()
    base_std = float(base_series.std())
    if not np.isfinite(base_std) or base_std <= 1e-12:
        return []

    # 3) đoạn tag tối thiểu phải đủ dài tương ứng min_hours giờ
    min_seg_points = _points_for_minutes(x.index, minutes=min_hours * 60, min_points=4)

    out: List[OscillationEvent] = []
    for (i, j) in segs:
        seg = x.iloc[i:j]
        mseg = mwx.iloc[i:j]

        seg = seg.dropna()
        mseg = mseg.dropna()

        if seg.size < min_seg_points:
            continue

        seg_std = float(seg.std())
        ratio = seg_std / base_std
        flips = _count_flips(seg)

        if ratio >= std_ratio_thr and flips >= flips_thr:
            mw_level = float(np.median(mseg.to_numpy())) if mseg.size else None
            out.append(
                OscillationEvent(
                    tag,
                    _fmt_ts(seg.index.min()),
                    _fmt_ts(seg.index.max()),
                    float(ratio),
                    int(flips),
                    mw_level,
                )
            )

    out.sort(key=lambda e: (e.std_ratio, e.flips), reverse=True)
    return out[:3]