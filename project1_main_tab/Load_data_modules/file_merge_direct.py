# file_merge_util.py

import pandas as pd
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QMessageBox

def select_files_and_merge(parent_widget, read_flexible_description_csv):
    """
    Hiện hộp thoại chọn file, đọc từng file (qua hàm read_flexible_description_csv),
    gộp ngang, trả về DataFrame kết quả (hoặc None nếu lỗi).
    """
    file_paths, _ = QFileDialog.getOpenFileNames(
        parent_widget,
        "Chọn các file dữ liệu để gộp ngang",
        "",
        "Dữ liệu (*.csv *.xlsm *.xlsb *.xlsx)"
    )

    if not file_paths:
        QMessageBox.information(parent_widget, "Thông báo", "Không có file nào được chọn.")
        return None

    dfs = []
    for path_str in file_paths:
        filepath = Path(path_str)
        try:
            df = read_flexible_description_csv(filepath)
            df = df.drop(columns=["SourceFile"], errors="ignore")
            dfs.append(df)
        except Exception as e:
            print(f"❌ Lỗi xử lý file {filepath.name}: {e}")

    if not dfs:
        QMessageBox.warning(parent_widget, "Không có dữ liệu", "Không có file dữ liệu hợp lệ.")
        return None

    merged_df = dfs[0]
    for df in dfs[1:]:
        df = df.drop(columns=["SourceFile"], errors="ignore")
        merged_df = pd.merge(merged_df, df, on=["Date", "Time"], how="outer")

    if 'Datetime' not in merged_df.columns:
        merged_df['Datetime'] = pd.to_datetime(
            merged_df['Date'].astype(str).str.strip() + ' ' + merged_df['Time'].astype(str).str.strip(),
            dayfirst=True,
            format='%d/%m/%Y %H:%M:%S',
            errors='coerce'
        )
    merged_df = merged_df.sort_values(by='Datetime')
    cols = ['Datetime'] + [col for col in merged_df.columns if col not in ['Datetime', 'Date', 'Time']]
    merged_df = merged_df[cols]

    return merged_df
