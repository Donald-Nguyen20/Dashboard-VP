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

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence

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
) -> tuple[dict[str, dict[int, Record]], dict[str, TagInfo]]:
    samples: dict[str, dict[int, Record]] = {tn: {} for tn in tag_names}
    tag_meta: dict[str, TagInfo] = {}

    files = folder.files_in_range(start, end)
    if not files:
        return samples, tag_meta

    start_unix = int(start.timestamp())
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
                bucket = samples[tag.tag_name]
                for rec in dsh.iter_records_for_tag(
                    tag, start_unix=start_unix, end_unix=end_unix
                ):
                    bucket[rec.unix_time] = rec
        finally:
            dsh.close()

        if progress:
            progress((fi + 1) / len(files))

    return samples, tag_meta


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
    samples, meta = _collect_samples(
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
                rec = samples.get(tag, {}).get(ts)
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


__all__ = [
    "SAMPLING_RATES_SEC", "END_OF_DATA_MARKER",
    "ExportRequest", "export_trend_csv",
]
