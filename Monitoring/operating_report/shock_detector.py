from __future__ import annotations
from typing import List
import numpy as np
import pandas as pd
from .types import ShockEvent

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

def _rolling_mad(x: pd.Series, w: int) -> pd.Series:
    return x.rolling(window=w, min_periods=max(10, w // 3)).apply(
        lambda a: np.median(np.abs(a - np.median(a))), raw=True
    )

def detect_shocks(
    s: pd.Series,
    tag: str,
    window: int = 61,
    k: float = 8.0,
    max_events: int = 5,
) -> List[ShockEvent]:
    x = _to_num(s).dropna()
    if x.size < 80:
        return []

    med = _rolling_median(x, window)
    mad = _rolling_mad(x, window).replace(0, np.nan)
    diff = (x - med).abs()
    z = (diff / (mad + 1e-12)).replace([np.inf, -np.inf], np.nan)

    flags = (diff > k * mad).fillna(False)
    if not flags.any():
        return []

    idxs = z[flags].sort_values(ascending=False).head(max_events).index
    out: List[ShockEvent] = []
    for ix in idxs:
        out.append(ShockEvent(tag=tag, when=_fmt_ts(ix), value=float(x.loc[ix]), z=float(z.loc[ix])))
    return out