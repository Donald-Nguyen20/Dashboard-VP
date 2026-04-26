# LtdViewerPy

App Python (PySide6) đọc file **DSH** của TOSMAP-HMI / LTDV và xuất ra **CSV**
với cấu trúc tương đương phần mềm gốc *LtdViewer* (Toshiba TOSMAP).

## Đặc điểm

- Parser DSH thuần Python dùng `mmap` (giống cách LtdViewer gốc dùng MemoryMappedFile).
- Layout file đã được trích **trực tiếp** từ binary `LtdViewer.exe v22.01.74` (các hằng số `POS_*`, `*_SIZE`, `DSH_TAGINFO_TOP_ADRESS`, `DSH_RECORD_TOP_ADRESS`...). Không phỏng đoán.
- Quét toàn bộ thư mục `\TREND\`, hợp nhất tag, lọc theo khoảng thời gian, resample theo bước 1s → 2h.
- Format CSV xuất ra bám sát LtdViewer: 4 dòng header (Trend / Date+Time+tagNo / Description / Units), dữ liệu, kết thúc bằng `*** END OF DATA ***`.

## Cấu trúc thư mục

```
LtdViewerPy/
├── dsh_reader.py     # parser DSH (header, TagInfo, Record)
├── csv_exporter.py   # logic xuất CSV
├── main.py           # GUI PySide6
├── requirements.txt
└── README.md
```

## Cài đặt (Windows)

```powershell
cd C:\Users\Donald\Desktop\TOSMAP\LtdViewerPy
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy GUI

```powershell
python main.py
```

Trình tự sử dụng:

1. **Browse…** chọn thư mục TREND (chứa `HD????????_??????GMT.DSH`).
2. App tự liệt kê toàn bộ tag trong các file DSH và auto-fill from/to theo
   header file đầu / file cuối.
3. Tick các tag muốn xuất (có ô **Filter** lọc theo tên/mô tả).
4. Chọn **Sampling**, đặt **Group name**, chọn nơi lưu **Save to…**
5. Bấm **Export CSV**.

Tab **Inspect DSH** mở 1 file DSH và in nhanh metadata (header + 50 tag đầu).
Tiện cho việc kiểm tra format khi bạn có file DSH thật.

## Định dạng DSH (tham khảo)

```
File header  : 0..65535
    0    64   fileId (signature "DS_HIST_FILE,2")
    64   260  fileTitle
    324  4    beginTime  (uint32 unix time UTC)
    328  4    endTime    (uint32)
    332  4    tagCount   (uint32)
    336  4    allRecordCount
    340  4    fileStatus
    344  4    isSortedTagInfo

TagInfo array : 65536..  (mỗi entry 568 bytes, tối đa 40000 entries)
    0    44   tagName
    44   4    tagId
    48   4    suffixType
    52   20   pid
    72   84   description1
    156  84   description2
    240  84   description3
    324  20   onStatusName
    344  20   offStatusName
    364  20   units
    384  8    dispRangeUpper (double)
    392  8    dispRangeLower (double)
    400  4    numberOfDigits
    404  4    decimalPlace
    408  12   category1
    420  12   category2
    432  12   category3
    444  12   category4
    456  12   category5
    468  4    recordTopIndex  (vị trí record đầu của tag, đơn vị: record)
    472  4    recordCount
    476  4    dummy1
    480  84   suffixDescription
    564  4    dummy2

Records       : 22_806_528..  (mỗi record 24 bytes)
    0    4    unixTime  (uint32 UTC)
    4    2    msec      (uint16)
    6    2    dummy1
    8    4    status    (uint32, & 0x03000000 = invalid)
    12   4    dummy2
    16   8    value     (double)
```

## Lưu ý

- App này dành cho mục đích **tự đọc dữ liệu của bạn**, không phải bản
  thay thế thương mại của LtdViewer.
- Nếu file DSH thật có biến thể (ví dụ `DS_HIST_FILE,3` hoặc khác alignment)
  bạn cần cập nhật hằng số trong `dsh_reader.py`.
- Phần xuất Event log / SOE log / PFC chưa làm — bám theo lựa chọn ban đầu
  (Đọc DSH + xuất CSV). Có thể bổ sung sau.
