from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class ShockEvent:
    tag: str
    when: str
    value: float
    z: float

@dataclass
class OscillationEvent:
    tag: str
    start: str
    end: str
    std_ratio: float
    flips: int
    mw_level: Optional[float]

@dataclass
class TrendEvent:
    tag: str
    kind: str       # "MAX_UP" / "MIN_DOWN" / "UP" / "DOWN"
    span_desc: str  # "6 tháng" / "1–3 tháng" / ...
    slope_ratio: float