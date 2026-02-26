# ML_TAB/Steps/Step2/profile_report.py
from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd



def generate_profile_json(
    df: pd.DataFrame,
    *,
    title: str = "Step 2 — Data Profile",
    out_dir: str = "reports",
    json_name: str = "profile_report.json",
    html: bool = True,                # <-- BẬT HTML THEO MẶC ĐỊNH
    html_name: str = "profile_report.html",
    minimal: bool = True,
) -> Tuple[str, Optional[str]]:
    if df is None or df.empty:
        raise ValueError("DataFrame rỗng. Hãy nạp dữ liệu ở Step 1 trước.")
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    json_path = str(out / json_name)
    html_path = str(out / html_name) if html else None

    

    return json_path, html_path
