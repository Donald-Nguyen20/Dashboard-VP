---
description: Kiểm tra tĩnh code Python - syntax, lint, import cho Dashboard V4
---

# 🔍 Workflow: Kiểm Tra Code (/check-code)

## Bước 1 — Kiểm tra cú pháp (bắt buộc, chạy trước)

// turbo
```powershell
cd "e:\book\Vanphong\Dashboard\Dashboard V4"
python -m py_compile <đường_dẫn_file.py>
```
- ✅ Không output = không lỗi cú pháp
- ❌ Có lỗi → SyntaxError → sửa ngay trước khi tiếp tục

**Kiểm tra nhiều file cùng lúc:**
// turbo
```powershell
Get-ChildItem -Recurse -Filter "*.py" -Path "e:\book\Vanphong\Dashboard\Dashboard V4" |
  Where-Object { $_.FullName -notmatch '__pycache__' } |
  ForEach-Object { python -m py_compile $_.FullName; if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: $($_.FullName)" } }
```

---

## Bước 2 — Kiểm tra import và biến không dùng

// turbo
```powershell
python -m pyflakes <đường_dẫn_file.py>
```
Nếu `pyflakes` chưa cài:
```powershell
pip install pyflakes
```

---

## Bước 3 — Kiểm tra style (tùy chọn)

// turbo
```powershell
python -m flake8 --max-line-length=120 --ignore=E501,W503 <đường_dẫn_file.py>
```
Cài nếu chưa có:
```powershell
pip install flake8
```

**Các lỗi phổ biến cần bỏ qua trong dự án này:**
- `E501` — dòng quá dài (stylesheet inline thường dài)
- `W503` — ngắt dòng trước toán tử nhị phân

---

## Bước 4 — Đánh giá kết quả

| Trạng thái          | Hành động                                  |
|---------------------|--------------------------------------------|
| ✅ Tất cả pass       | Tiếp tục sang `/run-test`                  |
| ⚠️ Pyflakes warning  | Sửa import thừa, biến không dùng           |
| ❌ SyntaxError       | Sửa ngay, chạy lại Bước 1                 |
| ❌ Flake8 critical   | Sửa trước khi chạy thử                    |

---

## Checklist nhanh trước khi push

- [ ] `py_compile` không báo lỗi
- [ ] `pyflakes` không có critical warning
- [ ] Không có `import *`
- [ ] Không có biến tên `l`, `O`, `I` (dễ nhầm)
- [ ] Mọi hàm public đều có docstring
