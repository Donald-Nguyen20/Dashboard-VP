"""
dsh_reader.py
=============
Đọc file DSH (DS Historical) của TOSMAP-HMI / LTDV.

Layout (đã được trích trực tiếp từ binary LtdViewer.exe v22.01.74):

    File header  : 0..65535      (1 SYSTEM_ALLOCATION_BLOCK)
        offset  size  field
        0       64    fileId         (ASCII, signature "DS_HIST_FILE,2")
        64      260   fileTitle
        324     4     beginTime      (uint32 unix time)
        328     4     endTime        (uint32 unix time)
        332     4     tagCount       (uint32)
        336     4     allRecordCount (uint32)
        340     4     fileStatus     (uint32)
        344     4     isSortedTagInfo (uint32)

    TagInfo array: 65536..        (DSH_TAGINFO_TOP_ADRESS)
        Mỗi entry 568 bytes (TAG_INFO_SIZE), tối đa MAX_TAG_SUFFIX_NUM = 40000.
        offset  size  field
        0       44    tagName
        44      4     tagId        (uint32)
        48      4     suffixType   (uint32)
        52      20    pid
        72      84    description1
        156     84    description2
        240     84    description3
        324     20    onStatusName
        344     20    offStatusName
        364     20    units
        384     8     dispRangeUpper (double)
        392     8     dispRangeLower (double)
        400     4     numberOfDigits (uint32)
        404     4     decimalPlace   (uint32)
        408     12    category1
        420     12    category2
        432     12    category3
        444     12    category4
        456     12    category5
        468     4     recordTopIndex (uint32)  -- vị trí record đầu của tag (đơn vị: record)
        472     4     recordCount    (uint32)
        476     4     dummy1
        480     84    suffixDescription
        564     4     dummy2

    Records:      22,806,528..    (DSH_RECORD_TOP_ADRESS)
        Mỗi record 24 bytes (DSH_RECORD_SIZE).
        offset  size  field
        0       4     unixTime  (uint32)
        4       2     msec      (uint16)
        6       2     dummy1
        8       4     status    (uint32, 0 = OK; xem TAG_STATUS_*)
        12      4     dummy2
        16      8     value     (double)

Status flags (lấy từ DshFile):
    TAG_STATUS_STATION_BAD     = 0x01000000
    TAG_STATUS_POOR            = 0x02000000
    TAG_STATUS_FILE_NOT_FOUND  = 0x03000000
    TAG_STATUS_TAG_NOT_FOUND   = 0x02000000
"""

from __future__ import annotations

import mmap
import os
import re
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional


# --- Hằng số (giữ nguyên tên như binary) ---------------------------------
SYSTEM_ALLOCATION_BLOCK_SIZE = 65536
MAX_TAG_SUFFIX_NUM           = 40000
DSH_TAGINFO_TOP_ADRESS       = 65536
DSH_TAGINFO_SIZE             = 568   # = TAG_INFO_SIZE
DSH_RECORD_TOP_ADRESS        = 22_806_528
DSH_RECORD_SIZE              = 24

DSH_FILE_SIGNATURE = b"DS_HIST_FILE,2"

# Tag status bits
TAG_STATUS_STATION_BAD    = 0x01000000
TAG_STATUS_POOR           = 0x02000000
TAG_STATUS_FILE_NOT_FOUND = 0x03000000
TAG_STATUS_TAG_NOT_FOUND  = 0x02000000
UIC_BAD_STATUS_BITS       = 0x03000000  # đủ để coi là invalid

# Filename: HDyyyymmdd_HHMMSSGMT.DSH
DSH_FILENAME_RE = re.compile(
    r"^HD(?P<date>\d{8})_(?P<time>\d{6})GMT\.DSH$",
    re.IGNORECASE,
)


# --- Dataclasses ----------------------------------------------------------
@dataclass
class FileHeader:
    file_id: str
    file_title: str
    begin_time: int      # unix seconds (UTC)
    end_time: int
    tag_count: int
    all_record_count: int
    file_status: int
    is_sorted_tag_info: int

    @property
    def begin_dt(self) -> datetime:
        return datetime.fromtimestamp(self.begin_time, tz=timezone.utc)

    @property
    def end_dt(self) -> datetime:
        return datetime.fromtimestamp(self.end_time, tz=timezone.utc)


@dataclass
class TagInfo:
    index: int
    tag_name: str
    tag_id: int
    suffix_type: int
    pid: str
    description1: str
    description2: str
    description3: str
    on_status_name: str
    off_status_name: str
    units: str
    disp_range_upper: float
    disp_range_lower: float
    number_of_digits: int
    decimal_place: int
    category1: str
    category2: str
    category3: str
    category4: str
    category5: str
    record_top_index: int
    record_count: int
    suffix_description: str

    @property
    def categories(self) -> list[str]:
        return [c for c in (
            self.category1, self.category2, self.category3,
            self.category4, self.category5,
        ) if c]

    @property
    def description(self) -> str:
        parts = [p for p in (self.description1, self.description2, self.description3) if p]
        return " ".join(parts)


@dataclass
class Record:
    unix_time: int
    msec: int
    status: int
    value: float

    @property
    def is_valid(self) -> bool:
        return (self.status & UIC_BAD_STATUS_BITS) == 0

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.unix_time, tz=timezone.utc).replace(
            microsecond=self.msec * 1000
        )


# --- Reader ---------------------------------------------------------------
def _decode(buf: bytes) -> str:
    """Decode null-terminated bytes (try utf-8 first, fallback cp932/latin-1)."""
    raw = buf.split(b"\x00", 1)[0]
    for enc in ("utf-8", "cp932", "latin-1"):
        try:
            return raw.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace").strip()


class DshFile:
    """Đọc một file DSH bằng memory-map (giống LtdViewer gốc)."""

    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        self._fh = open(self.path, "rb")
        self._mm = mmap.mmap(self._fh.fileno(), 0, access=mmap.ACCESS_READ)
        self.header = self._read_header()
        if not self.header.file_id.startswith("DS_HIST_FILE"):
            raise ValueError(
                f"DSH file id error: {self.header.file_id!r} (expected DS_HIST_FILE,2)"
            )

    # context manager
    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def close(self):
        try:
            self._mm.close()
        finally:
            self._fh.close()

    # ---- Header ----
    def _read_header(self) -> FileHeader:
        mm = self._mm
        return FileHeader(
            file_id           = _decode(mm[0:64]),
            file_title        = _decode(mm[64:324]),
            begin_time        = struct.unpack_from("<I", mm, 324)[0],
            end_time          = struct.unpack_from("<I", mm, 328)[0],
            tag_count         = struct.unpack_from("<I", mm, 332)[0],
            all_record_count  = struct.unpack_from("<I", mm, 336)[0],
            file_status       = struct.unpack_from("<I", mm, 340)[0],
            is_sorted_tag_info= struct.unpack_from("<I", mm, 344)[0],
        )

    # ---- Tag info ----
    def iter_tags(self) -> Iterator[TagInfo]:
        n = min(self.header.tag_count, MAX_TAG_SUFFIX_NUM)
        for i in range(n):
            yield self.read_tag(i)

    def read_tag(self, index: int) -> TagInfo:
        if index < 0 or index >= MAX_TAG_SUFFIX_NUM:
            raise IndexError(index)
        base = DSH_TAGINFO_TOP_ADRESS + index * DSH_TAGINFO_SIZE
        mm = self._mm
        d = mm[base : base + DSH_TAGINFO_SIZE]
        return TagInfo(
            index               = index,
            tag_name            = _decode(d[0:44]),
            tag_id              = struct.unpack_from("<I", d, 44)[0],
            suffix_type         = struct.unpack_from("<I", d, 48)[0],
            pid                 = _decode(d[52:72]),
            description1        = _decode(d[72:156]),
            description2        = _decode(d[156:240]),
            description3        = _decode(d[240:324]),
            on_status_name      = _decode(d[324:344]),
            off_status_name     = _decode(d[344:364]),
            units               = _decode(d[364:384]),
            disp_range_upper    = struct.unpack_from("<d", d, 384)[0],
            disp_range_lower    = struct.unpack_from("<d", d, 392)[0],
            number_of_digits    = struct.unpack_from("<I", d, 400)[0],
            decimal_place       = struct.unpack_from("<I", d, 404)[0],
            category1           = _decode(d[408:420]),
            category2           = _decode(d[420:432]),
            category3           = _decode(d[432:444]),
            category4           = _decode(d[444:456]),
            category5           = _decode(d[456:468]),
            record_top_index    = struct.unpack_from("<I", d, 468)[0],
            record_count        = struct.unpack_from("<I", d, 472)[0],
            suffix_description  = _decode(d[480:564]),
        )

    # ---- Records ----
    def read_record(self, record_index: int) -> Record:
        base = DSH_RECORD_TOP_ADRESS + record_index * DSH_RECORD_SIZE
        d = self._mm[base : base + DSH_RECORD_SIZE]
        return Record(
            unix_time = struct.unpack_from("<I", d, 0)[0],
            msec      = struct.unpack_from("<H", d, 4)[0],
            status    = struct.unpack_from("<I", d, 8)[0],
            value     = struct.unpack_from("<d", d, 16)[0],
        )

    def iter_records_for_tag(
        self,
        tag: TagInfo,
        *,
        start_unix: Optional[int] = None,
        end_unix: Optional[int] = None,
    ) -> Iterator[Record]:
        """Quét toàn bộ record block của tag và lọc theo thời gian (tuỳ chọn)."""
        for i in range(tag.record_count):
            rec = self.read_record(tag.record_top_index + i)
            if start_unix is not None and rec.unix_time < start_unix:
                continue
            if end_unix is not None and rec.unix_time > end_unix:
                break
            yield rec

    def get_records_for_tag(self, tag: TagInfo, **kw) -> list[Record]:
        return list(self.iter_records_for_tag(tag, **kw))


# --- Folder reader --------------------------------------------------------
class TrendFolderReader:
    """Quét toàn bộ thư mục TREND, sắp xếp DSH theo thời gian."""

    def __init__(self, trend_dir: str | os.PathLike):
        self.trend_dir = Path(trend_dir)
        self.files = self._scan()

    def _scan(self) -> list[Path]:
        if not self.trend_dir.is_dir():
            self._file_begin_unix: list[int] = []
            return []
        items: list[tuple[datetime, Path]] = []
        for p in self.trend_dir.iterdir():
            m = DSH_FILENAME_RE.match(p.name)
            if not m:
                continue
            try:
                dt = datetime.strptime(
                    m.group("date") + m.group("time"), "%Y%m%d%H%M%S"
                ).replace(tzinfo=timezone.utc)
                items.append((dt, p))
            except ValueError:
                continue
        items.sort(key=lambda x: x[0])
        self._file_begin_unix = [int(dt.timestamp()) for dt, _ in items]
        return [p for _dt, p in items]

    def files_in_range(self, start: datetime, end: datetime) -> list[Path]:
        """Trả về DSH file có begin_time/end_time chạm [start, end].
        Vì tên file = thời điểm bắt đầu, ta lấy mọi file mà tên <= end và file kế tiếp > start."""
        out: list[Path] = []
        bt = self._file_begin_unix
        for i, p in enumerate(self.files):
            file_dt = datetime.fromtimestamp(bt[i], tz=timezone.utc)
            nxt_dt = datetime.fromtimestamp(bt[i + 1], tz=timezone.utc) if i + 1 < len(self.files) else None
            if file_dt > end:
                break
            if nxt_dt is not None and nxt_dt <= start:
                continue
            out.append(p)
        return out

    def files_for_grid(self, start: datetime, end: datetime, step_sec: int) -> list[Path]:
        """Return only files needed for forward-fill at each step_sec grid point.

        For each grid point, keeps the last file whose begin_time <= grid_ts plus
        its predecessor (safety: file may start at grid_ts but first record arrives
        one recording interval later, so the prior file holds the actual last value).
        """
        candidates = self.files_in_range(start, end)
        n = len(candidates)
        if n <= 2:
            return candidates

        bt_map = {p: bt for p, bt in zip(self.files, self._file_begin_unix)}
        cb = [bt_map[p] for p in candidates]

        start_unix = int(start.timestamp())
        end_unix = int(end.timestamp())
        grid_start = (start_unix // step_sec) * step_sec

        needed: set[int] = set()
        for i in range(n):
            lo = max(cb[i], grid_start)
            hi = min(cb[i + 1] if i + 1 < n else end_unix + 1, end_unix + 1)
            # First grid point on the aligned grid that falls in [lo, hi)
            if lo <= grid_start:
                first_gp = grid_start
            else:
                first_gp = grid_start + ((lo - grid_start + step_sec - 1) // step_sec) * step_sec
            if first_gp < hi:
                needed.add(i)
                if i > 0:
                    needed.add(i - 1)

        return [candidates[i] for i in sorted(needed)] if needed else candidates


__all__ = [
    "DshFile", "TrendFolderReader",
    "FileHeader", "TagInfo", "Record",
    "TAG_STATUS_STATION_BAD", "TAG_STATUS_POOR",
    "TAG_STATUS_FILE_NOT_FOUND", "TAG_STATUS_TAG_NOT_FOUND",
    "UIC_BAD_STATUS_BITS",
]
