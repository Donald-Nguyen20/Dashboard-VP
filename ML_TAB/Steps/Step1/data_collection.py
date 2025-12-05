# ML_TAB/Steps/Step1/data_collection.py
import pandas as pd
from pathlib import Path

def load_rawdata(file_path: str):
    """
    Step 1 - Data Collection (Excel & CSV only)
    -------------------------------------------
    Đọc file CSV hoặc Excel và trả về DataFrame tên Rawdata.
    - Tự động nhận dạng định dạng theo phần mở rộng (.csv / .xlsx / .xls)
    - Chuẩn hoá tên cột (bỏ khoảng trắng, ký tự đặc biệt)
    """

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    ext = path.suffix.lower()
    if ext == ".csv":
        Rawdata = pd.read_csv(path, encoding="utf-8", low_memory=False)
    elif ext in [".xlsx", ".xls"]:
        Rawdata = pd.read_excel(path)
    else:
        raise ValueError("Chỉ hỗ trợ file CSV hoặc Excel (.csv, .xlsx, .xls).")

    # Chuẩn hoá tên cột cơ bản
    Rawdata.columns = [
        c.strip().replace(" ", "_").replace("-", "_") for c in Rawdata.columns
    ]

    return Rawdata
