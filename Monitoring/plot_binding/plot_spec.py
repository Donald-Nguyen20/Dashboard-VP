from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class PlotSpec:
    chart_type: str
    selected_vars: List[str]
    hue: str = "❌ Không phân loại"
    bar_color: Optional[str] = None
    scales: Dict[str, float] = None
    start_dt_iso: Optional[str] = None
    end_dt_iso: Optional[str] = None
    time_ranges_iso: Optional[List[Tuple[str, str]]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["scales"] = d["scales"] or {}
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PlotSpec":
        return PlotSpec(
            chart_type=d.get("chart_type", "line"),
            selected_vars=list(d.get("selected_vars", [])),
            hue=d.get("hue", "❌ Không phân loại"),
            bar_color=d.get("bar_color"),
            scales=d.get("scales") or {},
            start_dt_iso=d.get("start_dt_iso"),
            end_dt_iso=d.get("end_dt_iso"),
            time_ranges_iso=d.get("time_ranges_iso"),
        )