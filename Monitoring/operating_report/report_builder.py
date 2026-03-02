from __future__ import annotations
from typing import List, Optional
import pandas as pd

from .shock_detector import detect_shocks
from .oscillation_detector import detect_oscillation_when_mw_stable
# from .trend_detector import detect_trend_extremes, detect_trend_max_min_6m
from .local_trend_detector import detect_recent_trend_longest_months
def _infer_time_col(df: pd.DataFrame) -> Optional[str]:
    for cand in ("Datetime", "datetime", "DATE_TIME", "Time", "time", "timestamp", "Timestamp"):
        if cand in df.columns:
            return cand
    return None

def _fmt_ts(t) -> str:
    try:
        if isinstance(t, pd.Timestamp):
            return t.strftime("%Y-%m-%d %H:%M:%S")
        return str(t)
    except Exception:
        return str(t)

def build_operating_report(
    df_range: pd.DataFrame,
    tags: List[str],
    time_col: Optional[str] = None,
    mw_col: Optional[str] = None,
) -> str:
    if df_range is None or df_range.empty:
        return "Không có dữ liệu trong khung thời gian đã chọn."

    time_col = time_col or _infer_time_col(df_range)
    d = df_range.copy()

    if time_col and time_col in d.columns:
        d[time_col] = pd.to_datetime(d[time_col], errors="coerce")
        d = d.dropna(subset=[time_col]).sort_values(time_col).set_index(time_col)

    mw = d[mw_col] if (mw_col and mw_col in d.columns) else None

    # Header
    if isinstance(d.index, pd.DatetimeIndex) and len(d.index) > 0:
        hdr = f"Khung thời gian: {_fmt_ts(d.index.min())} → {_fmt_ts(d.index.max())}"
    else:
        hdr = "Khung thời gian: (không xác định datetime index)"
    lines = [f"<b>BÁO CÁO TRẠNG THÁI VẬN HÀNH</b><br>{hdr}<br><br>"]

    # Span descriptor
    span_desc = ""
    if isinstance(d.index, pd.DatetimeIndex) and len(d.index) > 1:
        span = d.index.max() - d.index.min()
        if span >= pd.Timedelta(days=150):
            span_desc = "6 tháng"
        elif span >= pd.Timedelta(days=30):
            span_desc = "1–3 tháng"
        elif span >= pd.Timedelta(days=7):
            span_desc = "1–4 tuần"
        else:
            span_desc = "ngắn hạn"
    else:
        span_desc = "khoảng thời gian chọn"

    shock_lines, osc_lines, trend_lines = [], [], []

    for tag in tags:
        if tag not in d.columns:
            continue
        s = d[tag]

        # 1) Shock
        for ev in detect_shocks(s, tag=tag):
            shock_lines.append(
                f"• <b>{ev.tag}</b> có <b>shock/spike</b> lúc <b>{ev.when}</b> (value={ev.value:.3f}, z≈{ev.z:.1f})."
            )

        # 2) Oscillation when MW stable
        for ev in detect_oscillation_when_mw_stable(s, tag=tag, mw_s=mw):
            if ev.mw_level is not None:
                osc_lines.append(
                    f"• <b>{ev.tag}</b> <b>dao động lớn</b> (std_ratio≈{ev.std_ratio:.2f}, {ev.flips} lần đổi chiều) "
                    f"trong <b>{ev.start} → {ev.end}</b> khi MW <b>ổn định</b> quanh ~<b>{ev.mw_level:.1f}</b>."
                )
            else:
                osc_lines.append(
                    f"• <b>{ev.tag}</b> <b>dao động lớn</b> ({ev.flips} lần đổi chiều) trong <b>{ev.start} → {ev.end}</b>."
                )

        # # 3) Trend
        # if span_desc == "6 tháng":
        #     for tr in detect_trend_max_min_6m(s, tag=tag, span_desc="6 tháng"):
        #         if tr.kind == "MAX_UP":
        #             trend_lines.append(
        #                 f"• <b>{tr.tag}</b>: <b>giá trị max tăng dần</b> trong <b>{tr.span_desc}</b> (mức độ≈{tr.slope_ratio:.2f})."
        #             )
        #         elif tr.kind == "MIN_DOWN":
        #             trend_lines.append(
        #                 f"• <b>{tr.tag}</b>: <b>giá trị min giảm dần</b> trong <b>{tr.span_desc}</b> (mức độ≈{tr.slope_ratio:.2f})."
        #             )
        # else:
        #     for tr in detect_trend_extremes(s, tag=tag, span_desc=span_desc, resample_rule="1D"):
        #         if tr.kind == "UP":
        #             trend_lines.append(
        #                 f"• <b>{tr.tag}</b>: có <b>xu hướng tăng</b> ({tr.span_desc}, mức độ≈{tr.slope_ratio:.2f})."
        #             )
        #         elif tr.kind == "DOWN":
        #             trend_lines.append(
        #                 f"• <b>{tr.tag}</b>: có <b>xu hướng giảm</b> ({tr.span_desc}, mức độ≈{tr.slope_ratio:.2f})."
        #             )
         # 3b) Recent trend >= 3 months (báo theo số tháng LỚN NHẤT)
        hit = detect_recent_trend_longest_months(
            s, tag=tag,
            min_months=3,
            max_months=12,          # anh muốn quét tối đa bao nhiêu tháng thì chỉnh đây
            slope_ratio_thr=0.18    # ngưỡng báo
        )
        if hit:
            if hit.direction == "DOWN":
                trend_lines.append(
                    f"• <b>{tag}</b>: "
                    f"<span style='color:#d32f2f; font-weight:700;'>xu hướng giảm</span> "
                    f"trong <b>{hit.months} tháng gần nhất</b> "
                    f"(<b>{hit.start:%Y-%m-%d} → {hit.end:%Y-%m-%d}</b>, mức độ≈{hit.strength:.2f})."
                )
            else:
                trend_lines.append(
                    f"• <b>{tag}</b>: "
                    f"<span style='color:#2e7d32; font-weight:700;'>xu hướng tăng</span> "
                    f"trong <b>{hit.months} tháng gần nhất</b> "
                    f"(<b>{hit.start:%Y-%m-%d} → {hit.end:%Y-%m-%d}</b>, mức độ≈{hit.strength:.2f})."
                )
    # Compose
    if shock_lines:
        lines.append("<b>1) Shock / Spike</b><br>" + "<br>".join(shock_lines) + "<br><br>")
    else:
        lines.append("<b>1) Shock / Spike</b><br>• Không phát hiện shock đáng kể.<br><br>")

    if osc_lines:
        lines.append("<b>2) Dao động lớn khi MW ổn định</b><br>" + "<br>".join(osc_lines) + "<br><br>")
    else:
        lines.append("<b>2) Dao động lớn khi MW ổn định</b><br>• Không phát hiện dao động bất thường trong các đoạn MW ổn định.<br><br>")

    if trend_lines:
        lines.append("<b>3) Xu hướng</b><br>" + "<br>".join(trend_lines) + "<br><br>")
    else:
        lines.append("<b>3) Xu hướng</b><br>• Không phát hiện xu hướng rõ ràng theo ngưỡng hiện tại.<br><br>")

    # lines.append("<i>Ghi chú:</i> Các ngưỡng (shock k, std_ratio, flips, …) có thể tinh chỉnh theo từng hệ thống/thiết bị.")
    return "".join(lines)