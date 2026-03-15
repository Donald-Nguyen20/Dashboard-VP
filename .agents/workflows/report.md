---
description: Tạo báo cáo kết quả sau khi hoàn thành viết và kiểm tra code Dashboard V4
---

# 📊 Workflow: Báo Cáo Kết Quả (/report)

## Mục đích

Sau khi hoàn tất các bước viết code, kiểm tra và chạy thử, tạo báo cáo **walkthrough.md** để lưu lại những gì đã làm.

---

## Bước 1 — Tạo file walkthrough.md

Tạo `walkthrough.md` trong artifact directory của conversation hiện tại.

**Template:**
```markdown
# Walkthrough — <Tên tính năng/Lỗi đã sửa>
**Ngày:** <ngày giờ hiện tại>
**Dự án:** Dashboard V4

---

## Tóm tắt

<Mô tả ngắn về việc đã làm>

---

## Thay đổi

| File | Thay đổi |
|------|----------|
| [tên_file.py](link_đến_file) | Thêm / sửa / xóa gì |

### Chi tiết thay đổi
render_diffs(file:///đường/dẫn/file_đã_sửa.py)

---

## Kết quả kiểm tra

### ✅ Syntax Check (py_compile)
- Tất cả file: PASS

### ✅ Lint Check (pyflakes)
- Không có warning nghiêm trọng

### ✅ Chạy thử ứng dụng
- Khởi động: OK
- Tính năng [X]: hoạt động đúng
- Tab [Y]: hiển thị dữ liệu đúng

---

## Ghi chú / Cảnh báo

> [!NOTE]
> Các ghi chú kỹ thuật cần lưu ý về thay đổi này

---

## Screenshot (nếu có)

![Kết quả](link_đến_screenshot)
```

---

## Bước 2 — Gửi kết quả cho người dùng

Dùng `notify_user` với:
- **PathsToReview**: đường dẫn đến `walkthrough.md`
- **Message** tóm tắt ngắn:
  - Đã làm gì
  - Kết quả pass/fail
  - Có vấn đề gì không

---

## Bước 3 — Lưu log vào thư mục dự án (tùy chọn)

// turbo
```powershell
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$logDir = "e:\book\Vanphong\Dashboard\Dashboard V4\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
# Sao chép walkthrough vào logs/
Copy-Item "<artifact_dir>\walkthrough.md" "$logDir\report_$timestamp.md"
Write-Host "✅ Log đã lưu tại: $logDir\report_$timestamp.md"
```
