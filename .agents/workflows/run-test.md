---
description: Chạy thử ứng dụng Dashboard V4, ghi log kết quả
---

# 🚀 Workflow: Chạy Thử (/run-test)

## Bước 1 — Chạy ứng dụng chính

// turbo
```powershell
cd "e:\book\Vanphong\Dashboard\Dashboard V4"
python project1_main.py
```

Quan sát:
- ✅ Cửa sổ mở ra không có lỗi = khởi động OK
- ❌ Traceback trong terminal = lỗi import hoặc runtime → xem Bước 4

---

## Bước 2 — Test thủ công từng tính năng

Thực hiện theo đúng tính năng vừa thêm / sửa:

**Load dữ liệu test:**
1. Click 📂 **Load Data** hoặc chọn folder từ sidebar trái
2. Các file CSV test nằm trong: `duchien/`, `Temp/`, hoặc folder riêng
3. Xác nhận dữ liệu hiện đúng ở Tab **🏠 Home**

**Kiểm tra từng Tab:**
| Tab | Kiểm tra |
|-----|----------|
| 🏠 Home | Load CSV, xem bảng, tìm kiếm |
| 🌐 Plotly | Chọn biến, vẽ biểu đồ, zoom/pan |
| 🔄 Drift Monitor | Load 2 dataset, so sánh drift |
| 🔮 Predict | Chạy model dự đoán |
| 📊 Analysis Report | Xuất báo cáo |

---

## Bước 3 — Ghi log kết quả

Ghi lại vào `walkthrough.md`:
```
## Kết quả chạy thử - <ngày giờ>

### ✅ Pass
- Ứng dụng khởi động thành công
- Tab [tên] hoạt động đúng với dữ liệu test
- Tính năng [tên] hoạt động đúng kỳ vọng

### ⚠️ Vấn đề phát hiện
- [Mô tả vấn đề] tại [file:line]

### ❌ Lỗi
- [Traceback đầy đủ nếu có]
```

---

## Bước 4 — Xử lý lỗi runtime

Nếu có lỗi khi chạy, tìm traceback trong terminal:

```
Traceback (most recent call last):
  File "project1_main_tab/load_data.py", line 123, in load_csv
    ...
ValueError: ...
```

→ Đọc đúng file + dòng trong traceback
→ Sửa lỗi → Quay lại Bước 1

---

## Bước 5 — Chạy với master_window (nếu cần)

// turbo
```powershell
cd "e:\book\Vanphong\Dashboard\Dashboard V4"
python master_window.py
```
