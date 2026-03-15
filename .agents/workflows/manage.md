---
description: Quản lý toàn bộ vòng đời code - viết, kiểm tra, chạy thử và báo cáo kết quả cho dự án Dashboard V4
---

# 🎯 Workflow: Code Manager (/manage)

Workflow này điều phối toàn bộ quy trình: **Viết code → Kiểm tra → Chạy thử → Báo cáo kết quả**

---

## BƯỚC 1 — Nhận yêu cầu & Phân tích

1. Đọc yêu cầu từ người dùng. Xác định rõ:
   - **Mục tiêu**: cần thêm tính năng gì / sửa lỗi gì / refactor gì?
   - **File liên quan**: file nào cần tạo mới hoặc chỉnh sửa?
   - **Module bị ảnh hưởng**: tab nào, class nào, function nào?

2. Đọc các file Python liên quan trong dự án:
   - `project1_main.py` — cửa sổ chính / điều phối tab
   - `project1_main_tab/load_data.py` — load và làm sạch CSV
   - `project1_main_tab/plotly_tab.py` — tab biểu đồ Plotly
   - `project1_main_tab/drift_tab.py` — tab drift monitor
   - `project1_main_tab/predict_tab.py` — tab dự đoán
   - `project1_main_tab/analysis_report_tab.py` — tab báo cáo
   - `ML_TAB/` — các tab ML
   - `master_window.py` — cửa sổ master (nếu dùng)

3. Tạo `implementation_plan.md` trong artifact dir và chia sẻ với người dùng trước khi viết code.

---

## BƯỚC 2 — Viết Code

// turbo
4. Dùng workflow `/write-code` để viết code:
   ```
   # Áp dụng theo .agents/workflows/write-code.md
   ```
   - Mỗi hàm / class phải có **docstring** tiếng Việt + tiếng Anh
   - Style nhất quán với codebase (PySide6, Qt signals/slots, stylesheet dark theme)
   - Không thay đổi logic của các module không liên quan

---

## BƯỚC 3 — Kiểm tra Code (Static Check)

// turbo
5. Chạy kiểm tra cú pháp Python với `py_compile`:
   ```powershell
   python -m py_compile <đường_dẫn_file_vừa_sửa>
   ```
   Nếu có lỗi → quay lại Bước 2 sửa trước khi tiếp tục.

// turbo
6. Chạy `pyflakes` để tìm import thừa, biến không dùng:
   ```powershell
   python -m pyflakes <đường_dẫn_file>
   ```

7. (Tùy chọn) Chạy `pylint` hoặc `flake8` nếu đã cài:
   ```powershell
   python -m flake8 --max-line-length=120 <đường_dẫn_file>
   ```

---

## BƯỚC 4 — Chạy Thử Ứng Dụng

// turbo
8. Khởi động ứng dụng để kiểm tra trực quan:
   ```powershell
   cd "e:\book\Vanphong\Dashboard\Dashboard V4"
   python project1_main.py
   ```
   - Nếu ứng dụng khởi động thành công → qua Bước 5
   - Nếu có lỗi runtime → ghi lại traceback, quay lại Bước 2

9. Kiểm tra bằng tay (manual):
   - Mở tab liên quan
   - Load dữ liệu test từ thư mục `duchien/` hoặc `Temp/`
   - Thao tác tính năng vừa thêm / sửa

---

## BƯỚC 5 — Tạo Báo Cáo Kết Quả

10. Tạo `walkthrough.md` trong artifact dir với các mục:
    - **Tính năng đã thêm / lỗi đã sửa**
    - **File đã thay đổi** (có link đến file)
    - **Kết quả kiểm tra cú pháp** (pass/fail)
    - **Kết quả chạy thử** (pass/fail + screenshot nếu có)
    - **Ghi chú / cảnh báo** (nếu có breaking change)

11. Thông báo cho người dùng qua `notify_user` với tóm tắt và đường dẫn đến `walkthrough.md`.

---

## Sub-workflows
- 📝 `/write-code` — Hướng dẫn viết code sạch cho dự án này
- 🔍 `/check-code` — Kiểm tra tĩnh (syntax, lint)
- 🚀 `/run-test` — Chạy thử và ghi log
- 📊 `/report` — Tạo báo cáo kết quả
