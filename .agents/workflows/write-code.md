---
description: Hướng dẫn viết code sạch, nhất quán cho dự án Dashboard V4 (PySide6/Python)
---

# 📝 Workflow: Viết Code (/write-code)

## Quy tắc chung

1. **Đọc file gốc trước** — Dùng `view_file` để nắm rõ cấu trúc file đang sửa.
2. **Không xóa code cũ** nếu chưa chắc — Comment lại với lý do rõ ràng.
3. **Một hàm = một mục đích** — Hàm quá dài (>80 dòng) → tách ra.

---

## Chuẩn style cho dự án này

### Imports
```python
# Stdlib trước
import sys
from pathlib import Path

# Third-party
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt

# Internal modules
from project1_main_tab.load_data import CsvCleanerWidget
```

### Docstring (bắt buộc với class và hàm public)
```python
def update_variables(self, df):
    """
    Cập nhật DataFrame khi người dùng load dữ liệu mới.
    Updates the DataFrame when the user loads new data.

    Args:
        df (pd.DataFrame): DataFrame mới từ CsvCleanerWidget.
    """
    self.df = df
    self._refresh_ui()
```

### Stylesheet (nhất quán dark theme)
```python
# Màu chuẩn của dự án:
# Background chính  : #1a1c29
# Background phụ   : #0f111a
# Border            : #2a2e45
# Accent primary    : #00bcd4 (cyan)
# Accent secondary  : #8c5eff (purple)
# Text chính        : #e0e3f0

widget.setStyleSheet("""
    QWidget {
        background-color: #1a1c29;
        color: #e0e3f0;
    }
""")
```

### Xử lý lỗi
```python
try:
    result = some_operation()
except Exception as e:
    print(f"[ERROR] {__name__}: {e}")
    # Hoặc hiện QMessageBox nếu cần báo người dùng
```

---

## Thêm Tab mới

1. Tạo file `project1_main_tab/<tên_tab>.py` với class kế thừa `QWidget`.
2. Implement method `update_variables(self, df)` để nhận dữ liệu từ MainWindow.
3. Trong `project1_main.py`, thêm vào `add_tabs()`:
   ```python
   self.new_tab = NewTab(parent=self)
   self.tab_widget.addTab(self.new_tab, "🆕 Tab Name")
   ```
4. Trong `set_final_df()`, gọi update cho tab mới:
   ```python
   if hasattr(self, "new_tab"):
       self.new_tab.update_variables(df)
   ```

---

## Thêm tính năng vào Tab hiện có

1. Đọc file tab hiện tại với `view_file`.
2. Tìm đúng vị trí cần thêm (không thêm vào `__init__` nếu có thể tách hàm).
3. Dùng `multi_replace_file_content` để sửa nhiều chỗ cùng lúc.
4. Chạy syntax check ngay sau khi sửa (xem `/check-code`).
