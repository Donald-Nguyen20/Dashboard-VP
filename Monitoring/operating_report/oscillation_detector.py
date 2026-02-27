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
    return x.rolling(window=w, min_periods=max(5, w // 3), center=True).median()

def _count_flips(x: pd.Series) -> int:
    d = x.diff().dropna()
    if d.size < 10:
        return 0
    sign = np.sign(d.to_numpy())
    return int(np.sum((sign[1:] * sign[:-1]) < 0))

def _stable_mw_segments(
    mw: pd.Series,
    min_minutes: int,
    std_thr_ratio: float = 0.004,
    slope_thr_ratio: float = 0.003,
) -> List[Tuple[int, int]]:
    x = _to_num(mw)
    if x.dropna().size < 60:
        return []

    mw_med = float(np.median(x.dropna().to_numpy()))
    base = abs(mw_med) if abs(mw_med) > 1e-9 else float(x.dropna().std() + 1.0)

    w = max(10, int(min_minutes))
    roll_std = x.rolling(w, min_periods=max(5, w // 3)).std()
    roll_med = _rolling_median(x, w)
    roll_slope = roll_med.diff().abs()

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
    min_hours: int = 1,
    std_ratio_thr: float = 2.0,
    flips_thr: int = 6,
) -> List[OscillationEvent]:
    x = _to_num(tag_s)
    if x.dropna().size < 100:
        return []

    base_std = float(x.dropna().std())
    if not np.isfinite(base_std) or base_std <= 1e-12:
        return []

    if mw_s is None:
        flips = _count_flips(x.dropna())
        if flips >= flips_thr:
            return [OscillationEvent(tag, _fmt_ts(x.index.min()), _fmt_ts(x.index.max()), 1.0, flips, None)]
        return []

    mwx = _to_num(mw_s)
    segs = _stable_mw_segments(mwx, min_minutes=min_hours * 60)
    if not segs:
        return []

    out: List[OscillationEvent] = []
    for (i, j) in segs:
        seg = x.iloc[i:j].dropna()
        if seg.size < 60:
            continue

        seg_std = float(seg.std())
        ratio = seg_std / base_std
        flips = _count_flips(seg)

        if ratio >= std_ratio_thr and flips >= flips_thr:
            mw_level = float(np.median(mwx.iloc[i:j].dropna().to_numpy())) if mwx.iloc[i:j].dropna().size else None
            out.append(OscillationEvent(tag, _fmt_ts(seg.index.min()), _fmt_ts(seg.index.max()),
                                       float(ratio), int(flips), mw_level))

    out.sort(key=lambda e: (e.std_ratio, e.flips), reverse=True)
    return out[:3]