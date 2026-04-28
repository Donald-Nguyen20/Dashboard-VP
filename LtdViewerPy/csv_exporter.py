"""
csv_exporter.py
===============
Xuất dữ liệu Trend ra file CSV với cấu trúc tương đương LtdViewer gốc:

    "Trend","<group_name>"
    "Date","Time","<tag1>","<tag2>",...
    "","" ,"<desc1>","<desc2>",...
    "","" ,"<unit1>","<unit2>",...
    yyyy/mm/dd,hh:mm:ss,v1,v2,...
    ...
    "*** END OF DATA ***"
"""

from __future__ import annotations

import bisect
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence

import pandas as pd

from .dsh_reader import (
    DshFile, Record, TagInfo, TrendFolderReader,
)


SAMPLING_RATES_SEC = {
    "1sec":   1,
    "2sec":   2,
    "5sec":   5,
    "10sec":  10,
    "15sec":  15,
    "30sec":  30,
    "1min":   60,
    "2min":   120,
    "5min":   300,
    "10min":  600,
    "15min":  900,
    "30min":  1800,
    "1hour":  3600,
    "2hour":  7200,
}

END_OF_DATA_MARKER = "*** END OF DATA ***"


@dataclass
class ExportRequest:
    output_path: Path
    group_name: str
    start: datetime
    end: datetime
    sampling_sec: int
    tags: Sequence[str]


def _format_value(value: float, decimal_place: int) -> str:
    if decimal_place <= 0:
        return f"{int(round(value))}"
    return f"{value:.{decimal_place}f}"


def _collect_samples(
    folder: TrendFolderReader,
    tag_names: Sequence[str],
    start: datetime,
    end: datetime,
    *,
    progress: Optional[Callable[[float], None]] = None,
) -> tuple[dict[str, list[int]], dict[str, list[Record]], dict[str, TagInfo]]:
    """Quét records cho mỗi tag, trả về 2 list song song đã sort theo unix_time.

    Returns (sample_times, sample_records, tag_meta) — sample_times[tag] và
    sample_records[tag] cùng chiều dài, sort tăng dần theo unix_time. Để hỗ trợ
    forward-fill ở mốc lưới đầu tiên, KHÔNG filter records theo start_unix; chỉ
    cắt ở end_unix để tránh load đuôi file vô ích.
    """
    sample_times: dict[str, list[int]] = {tn: [] for tn in tag_names}
    sample_records: dict[str, list[Record]] = {tn: [] for tn in tag_names}
    tag_meta: dict[str, TagInfo] = {}

    files = folder.files_in_range(start, end)
    if not files:
        return sample_times, sample_records, tag_meta

    end_unix = int(end.timestamp())

    for fi, fpath in enumerate(files):
        try:
            dsh = DshFile(fpath)
        except Exception:
            continue
        try:
            wanted = set(tag_names)
            for tag in dsh.iter_tags():
                if tag.tag_name not in wanted:
                    continue
                if tag.tag_name not in tag_meta:
                    tag_meta[tag.tag_name] = tag
                tlist = sample_times[tag.tag_name]
                rlist = sample_records[tag.tag_name]
                for rec in dsh.iter_records_for_tag(
                    tag, start_unix=None, end_unix=end_unix
                ):
                    tlist.append(rec.unix_time)
                    rlist.append(rec)
        finally:
            dsh.close()

        if progress:
            progress((fi + 1) / len(files))

    # Sort lại defensively: TrendFolderReader đã trả file theo thứ tự thời gian,
    # và records trong từng file vốn đã sort, nên ts_list thường đã sort. Tuy
    # nhiên record ở đường biên (vd 16:00:00 có ở cả file 15:00 và 16:00) có
    # thể trùng unix_time -> stable sort giữ thứ tự (file sau ghi đè file
    # trước khi lookup vì bisect_right trả index lớn nhất với ts <= mốc).
    for tn in tag_names:
        ts_list = sample_times[tn]
        if len(ts_list) <= 1:
            continue
        order = sorted(range(len(ts_list)), key=lambda i: ts_list[i])
        sample_times[tn] = [ts_list[i] for i in order]
        sample_records[tn] = [sample_records[tn][i] for i in order]

    return sample_times, sample_records, tag_meta


def _lookup_record(
    sample_times: dict[str, list[int]],
    sample_records: dict[str, list[Record]],
    tag: str,
    ts: int,
) -> Optional[Record]:
    """Trả về record có unix_time lớn nhất nhưng <= ts (forward-fill).

    Đây là semantic "instant value" của LtdViewer gốc: tại mốc lưới ts, lấy
    giá trị mới nhất đã được ghi cho tới thời điểm đó. Trả None nếu chưa có
    record nào tới mốc đó.
    """
    arr = sample_times.get(tag)
    if not arr:
        return None
    i = bisect.bisect_right(arr, ts) - 1
    if i < 0:
        return None
    return sample_records[tag][i]


def _resample_grid(start: datetime, end: datetime, step_sec: int) -> list[int]:
    s = (int(start.timestamp()) // step_sec) * step_sec
    e = int(end.timestamp())
    return list(range(s, e + 1, step_sec))


def export_trend_csv(
    request: ExportRequest,
    folder: TrendFolderReader,
    *,
    progress: Optional[Callable[[float], None]] = None,
) -> int:
    sample_times, sample_records, meta = _collect_samples(
        folder, request.tags, request.start, request.end, progress=progress
    )

    grid = _resample_grid(request.start, request.end, request.sampling_sec)

    out_path = Path(request.output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)

        w.writerow(["Trend", request.group_name])
        w.writerow(["Date", "Time"] + list(request.tags))
        w.writerow(["", ""] + [meta.get(t).description if t in meta else "" for t in request.tags])
        w.writerow(["", ""] + [meta.get(t).units if t in meta else "" for t in request.tags])

        # Data block.
        # NOTE: dùng "HH:MM:SS" (không có ".000"). Mọi sampling rate đều >= 1 giây
        # nên ms luôn = 000. Khi format "HH:MM:SS.000", Excel auto-detect là time
        # có sub-second và áp format "mm:ss.0" -> tất cả ô hiện "00:00.0".
        # Bỏ ".000" -> Excel dùng format mặc định "h:mm:ss" hiển thị đúng.
        for ts in grid:
            row_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            date_str = row_dt.strftime("%Y/%m/%d")
            time_str = row_dt.strftime("%H:%M:%S")
            row = [date_str, time_str]
            for tag in request.tags:
                rec = _lookup_record(sample_times, sample_records, tag, ts)
                if rec is None or not rec.is_valid:
                    row.append("")
                else:
                    dp = meta[tag].decimal_place if tag in meta else 3
                    row.append(_format_value(rec.value, dp))
            w.writerow(row)
            rows_written += 1

        f.write(f"{END_OF_DATA_MARKER}\n")

    if progress:
        progress(1.0)
    return rows_written


def build_dataframe(
    request: ExportRequest,
    folder: TrendFolderReader,
    *,
    progress: Optional[Callable[[float], None]] = None,
) -> pd.DataFrame:
    sample_times, sample_records, meta = _collect_samples(
        folder, request.tags, request.start, request.end, progress=progress
    )
    grid = _resample_grid(request.start, request.end, request.sampling_sec)

    rows = []
    for ts in grid:
        row: dict = {"Datetime": datetime.fromtimestamp(ts, tz=timezone.utc)}
        for tag in request.tags:
            rec = _lookup_record(sample_times, sample_records, tag, ts)
            row[tag] = rec.value if (rec is not None and rec.is_valid) else None
        rows.append(row)

    df = pd.DataFrame(rows)

    # Đổi tên cột từ tag name → description (khớp với header CSV)
    rename_map = {tag: meta[tag].description for tag in request.tags if tag in meta and meta[tag].description}
    df = df.rename(columns=rename_map)

    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


__all__ = [
    "SAMPLING_RATES_SEC", "END_OF_DATA_MARKER",
    "ExportRequest", "export_trend_csv", "build_dataframe",
]
