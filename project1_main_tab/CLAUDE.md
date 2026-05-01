# [M02] & [M05] Data Acquisition & Shared Utilities

- **Mục đích**: Xử lý dữ liệu đầu vào (CSV/Excel), cache Parquet, quản lý Global DataFrame. Chứa module tiện ích (UI, Plotly, Formulas).
- **Key Files**: `project1_main.py`, `Load_data_modules/`, `Plotly_modules/`, `Formula_modules/`.
- **Input/Output**: File thô (input) -> Global DataFrame state (output).
- **Dependencies**: Pandas, Plotly.

## ⛔ KHÔNG làm
- KHÔNG thay đổi cơ chế truyền dữ liệu callback `df_provider` nếu không cần thiết.
- KHÔNG tạo circular dependency ngược về `master_window.py`.
