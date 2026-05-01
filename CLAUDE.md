# Tổng quan dự án: Dashboard V4

- **Mục đích**: Hệ thống giám sát, phân tích dữ liệu và machine learning.
- **Stack**: Python, PySide6 (UI), Plotly, Pandas, HTML/JS/SVG (QWebEngineView).
- **Entry point**: `master_window.py`.
- **Thư mục bỏ qua**: `duchien - Copy` (⛔ KHÔNG đọc/sửa thư mục này).

## Module Map
- **[M01] Core Orchestration**: Giao diện chính, điều hướng (`master_window.py`).
- **[M02] Data Acquisition & Analysis**: Tải, gộp dữ liệu, quản lý DataFrame (`project1_main_tab/`, `LtdViewerPy/`).
- **[M03] Machine Learning**: Tiền xử lý, huấn luyện model (`ML_TAB/`).
- **[M04] Monitoring System**: Hiển thị SVG/HTML thời gian thực (`Monitoring/`, `Systems/`).
- **[M05] Shared Utilities**: Thành phần dùng chung (`project1_main_tab/Load_data_modules/`, `project1_main_tab/Plotly_modules/`, `project1_main_tab/Formula_modules/`).

## Cách chạy (How to run)
- **Lệnh đúng**: `.venv\Scripts\python master_window.py`
- **KHÔNG dùng** `python master_window.py` (python hệ thống thiếu dependencies)
- Virtual env: `.venv/` đã có sẵn trong thư mục dự án

## Lỗi thường gặp
- **DuckDB path**: path có dấu cách trên Windows → đã xử lý bằng list file trong `_read_expr()`
- **Qt cross-thread**: KHÔNG gọi UI widget trực tiếp từ thread khác → dùng Signal/Slot
- **QWebEngineView blank**: cần QApplication tồn tại trước khi tạo WebEngine widget
- **Date parse**: format mặc định `dd/MM/yyyy HH:MM:SS` (VN), dayfirst=True

## Khi Claude sửa sai
- Dùng `Ctrl+Z` trong VS Code để undo từng bước
- Hoặc: `git diff` để xem thay đổi, `git checkout -- <file>` để revert file cụ thể
- Với thay đổi lớn: commit trước khi yêu cầu Claude sửa (`git commit -am "backup before refactor"`)

## ⛔ KHÔNG làm (DO NOT)
- KHÔNG đọc, phân tích hay sửa thư mục `duchien - Copy`.
- KHÔNG tự ý thay đổi cấu trúc `MainWindow` hiện tại (dù nó là God Object).
- KHÔNG fix các Known Technical Debt nếu không được yêu cầu cụ thể.
- KHÔNG import PyQt5 — dự án dùng PySide6.
- KHÔNG đổi `id` các thẻ SVG trong `Systems/` (Python inject data qua id này).
