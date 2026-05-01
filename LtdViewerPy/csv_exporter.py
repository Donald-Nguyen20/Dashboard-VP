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
from concurrent.futures import ThreadPoolExecutor, as_completed
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


_IO_WORKERS = 16


def _read_one_file(
    fpath: Path,
    tag_names: Sequence[str],
    end_unix: int,
    step_sec: int,
) -> tuple[dict[str, list[int]], dict[str, list[Record]], dict[str, TagInfo]]:
    local_times: dict[str, list[int]] = {tn: [] for tn in tag_names}
    local_recs: dict[str, list[Record]] = {tn: [] for tn in tag_names}
    local_meta: dict[str, TagInfo] = {}
    try:
        dsh = DshFile(fpath)
        wanted = set(tag_names)
        try:
            for tag in dsh.iter_tags():
                if tag.tag_name not in wanted:
                    continue
                if tag.tag_name not in local_meta:
                    local_meta[tag.tag_name] = tag
                # Keep only the last record per step_sec bucket — avoids loading
                # thousands of records that will never be used by the grid lookup.
                bucket_ts: dict[int, int] = {}
                bucket_rec: dict[int, Record] = {}
                for rec in dsh.iter_records_for_tag(tag, start_unix=None, end_unix=end_unix):
                    b = rec.unix_time // step_sec
                    bucket_ts[b] = rec.unix_time
                    bucket_rec[b] = rec
                tlist = local_times[tag.tag_name]
                rlist = local_recs[tag.tag_name]
                for b in sorted(bucket_ts):
                    tlist.append(bucket_ts[b])
                    rlist.append(bucket_rec[b])
        finally:
            dsh.close()
    except Exception:
        pass
    return local_times, local_recs, local_meta


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
    step_sec: int,
    progress: Optional[Callable[[float], None]] = None,
) -> tuple[dict[str, list[int]], dict[str, list[Record]], dict[str, TagInfo]]:
    sample_times: dict[str, list[int]] = {tn: [] for tn in tag_names}
    sample_records: dict[str, list[Record]] = {tn: [] for tn in tag_names}
    tag_meta: dict[str, TagInfo] = {}

    files = folder.files_for_grid(start, end, step_sec)
    if not files:
        return sample_times, sample_records, tag_meta

    end_unix = int(end.timestamp())
    n = len(files)
    workers = min(_IO_WORKERS, n)
    completed = 0

    results: list[tuple | None] = [None] * n
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_idx = {
            pool.submit(_read_one_file, fpath, tag_names, end_unix, step_sec): fi
            for fi, fpath in enumerate(files)
        }
        for future in as_completed(future_to_idx):
            fi = future_to_idx[future]
            try:
                results[fi] = future.result()
            except Exception:
                results[fi] = ({tn: [] for tn in tag_names}, {tn: [] for tn in tag_names}, {})
            completed += 1
            if progress:
                progress(completed / n)

    for res in results:
        if res is None:
            continue
        lt, lr, lm = res
        for tn in tag_names:
            sample_times[tn].extend(lt[tn])
            sample_records[tn].extend(lr[tn])
        for k, v in lm.items():
            if k not in tag_meta:
                tag_meta[k] = v

    # Sort then deduplicate by bucket across file boundaries: keep the latest
    # record per step_sec bucket so the merged list is as compact as the grid.
    for tn in tag_names:
        ts_list = sample_times[tn]
        rec_list = sample_records[tn]
        if len(ts_list) <= 1:
            continue
        order = sorted(range(len(ts_list)), key=lambda i: ts_list[i])
        ts_sorted = [ts_list[i] for i in order]
        rec_sorted = [rec_list[i] for i in order]

        dedup_ts: list[int] = []
        dedup_rec: list[Record] = []
        prev_bucket = -1
        for ts, rec in zip(ts_sorted, rec_sorted):
            b = ts // step_sec
            if b == prev_bucket:
                dedup_ts[-1] = ts
                dedup_rec[-1] = rec
            else:
                dedup_ts.append(ts)
                dedup_rec.append(rec)
                prev_bucket = b
        sample_times[tn] = dedup_ts
        sample_records[tn] = dedup_rec

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
        folder, request.tags, request.start, request.end,
        step_sec=request.sampling_sec, progress=progress,
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
        folder, request.tags, request.start, request.end,
        step_sec=request.sampling_sec, progress=progress,
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

    for i in range(1, len(df.columns)):
        df.iloc[:, i] = pd.to_numeric(df.iloc[:, i], errors="coerce")

    return df


__all__ = [
    "SAMPLING_RATES_SEC", "END_OF_DATA_MARKER",
    "ExportRequest", "export_trend_csv", "build_dataframe",
]
