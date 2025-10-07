from PySide6.QtWidgets import QMessageBox, QInputDialog
from pathlib import Path
import pandas as pd
import json
import re

def insert_formula_feature(df: pd.DataFrame, parent_widget) -> pd.DataFrame:
    formula_folder = Path("formulas")
    if not formula_folder.exists():
        QMessageBox.warning(parent_widget, "Không có công thức", "Thư mục 'formulas/' không tồn tại.")
        return df

    formula_files = list(formula_folder.glob("*.json"))
    if not formula_files:
        QMessageBox.warning(parent_widget, "Không có công thức", "Chưa có công thức nào được lưu.")
        return df

    choices = [f.stem for f in formula_files]
    formula_name, ok = QInputDialog.getItem(parent_widget, "Chọn công thức", "Công thức:", choices, 0, False)
    if not ok:
        return df

    path = formula_folder / f"{formula_name}.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    formulas = data if isinstance(data, list) else [data]

    added_cols = []
    for formula in formulas:
        formula_expr = formula.get("formula_expr") or formula.get("formula")
        alert_cond = formula.get("alert_condition", "")
        new_col_name = formula.get("formula_name") or formula_name

        if not formula_expr:
            QMessageBox.warning(parent_widget, "Lỗi công thức", f"Không tìm thấy biểu thức trong file: {path}")
            continue

        # Tự động lấy danh sách cột cần thiết từ công thức (giữa dấu ` `)
        formula_cols = re.findall(r'`([^`]+)`', formula_expr)
        # Chuẩn hóa tên cột (loại bỏ khoảng trắng đầu/cuối)
        df.columns = [col.strip() for col in df.columns]

        # Cảnh báo nếu thiếu cột
        missing_cols = [col for col in formula_cols if col not in df.columns]
        if missing_cols:
            QMessageBox.critical(
                parent_widget, "Thiếu cột",
                f"Các cột sau không có trong dữ liệu:\n" + "\n".join(missing_cols)
            )
            continue

        # Ép kiểu numeric các cột này
        for col in formula_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Tính công thức!
        try:
            result = df.eval(formula_expr, engine="python")
            df[new_col_name] = result
            added_cols.append(new_col_name)
        except Exception as e:
            # In rõ lỗi và dtypes liên quan để debug nếu vẫn lỗi
            dtype_info = df[formula_cols].dtypes.to_string()
            msg = f"Không thể tính công thức '{new_col_name}':\n{e}\n\nKiểu dữ liệu thực tế:\n{dtype_info}"
            QMessageBox.critical(parent_widget, "Lỗi tính toán", msg)
            continue

        # Nếu có điều kiện cảnh báo
        if alert_cond:
            try:
                alert_mask = df.eval(alert_cond, engine="python")
                df[f"{new_col_name}_alert"] = alert_mask.astype(bool)
            except Exception as e:
                QMessageBox.warning(parent_widget, "Cảnh báo công thức",
                    f"Không thể áp dụng điều kiện cảnh báo cho '{new_col_name}':\n{e}")

    if added_cols:
        QMessageBox.information(parent_widget, "Thành công",
            f"✅ Đã thêm các cột: {', '.join(added_cols)} vào bảng.")
    else:
        QMessageBox.warning(parent_widget, "Thất bại", "Không có công thức nào được áp dụng thành công.")

    return df
