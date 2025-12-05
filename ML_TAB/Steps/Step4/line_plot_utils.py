# file: ML_TAB/Steps/Step4/line_plot_utils.py

from __future__ import annotations

from typing import List, Optional, Dict

import pandas as pd

# Những cột KHÔNG dùng để vẽ trực tiếp
IGNORED_COLUMNS = {"datetime", "date", "time", "sourcefolder"}


def plot_line_multi(
    ax,
    df: pd.DataFrame,
    variables: List[str],
    datetime_col: Optional[str],
    scales: Dict[str, float],
    source_text: str,
):
    """
    Hàm thuần để vẽ line:
    - x: Datetime (nếu có), ngược lại dùng index
    - y: nhiều biến overlay, có scale từng biến
    """
    ax.clear()

    # X = Datetime (nếu có), else index
    if datetime_col is not None and datetime_col in df.columns:
        x = df[datetime_col]
        ax.set_xlabel(datetime_col)
    else:
        x = df.index
        ax.set_xlabel("Index")

    for var in variables:
        if var not in df.columns:
            continue
        y = df[var]

        scale = scales.get(var, 1.0)
        y_plot = y * scale

        ax.plot(x, y_plot, label=f"{var} (x{scale})")

    ax.set_ylabel("Value")
    ax.set_title(f"Line chart — {source_text}")
    ax.grid(True)

