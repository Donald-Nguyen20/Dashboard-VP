"""
Script Automation: Điều khiển ngầm Dashboard V4 bằng code Python
Mục tiêu:
 1. Load data từ thư mục "duchien" sử dụng module load_data
 2. Chạy Forecasting cho AH O/L FG PRS sử dụng module forecasting_tab
 3. Không hiển thị cửa sổ nhập liệu, trích xuất dữ liệu tự động.
"""

import sys
import pandas as pd
from pathlib import Path
from PySide6.QtWidgets import QApplication

# Thêm đường dẫn dự án để import được các modules của Dashboard V4
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.append(str(PROJECT_ROOT))

# Import các components từ codebase
from project1_main_tab.load_data import CsvCleanerWidget
from project1_main_tab.Forecasting_modules.forecasting_tab import ForecastingTab

def run_automation():
    # 1. Khởi tạo một Application ảo ngầm vòng đời trọn vẹn để các components PySide6 không bị văng
    app = QApplication.instance() or QApplication(sys.argv)

    print("=" * 60)
    print("🤖 BẮT ĐẦU CHẠY AUTOMATION DASHBOARD V4")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # BƯỚC 1: LOAD DỮ LIỆU TỪ load_data_modules
    # -------------------------------------------------------------------------
    print("\n[BƯỚC 1] Khởi tạo CsvCleanerWidget và load data từ 'duchien'...")
    cleaner = CsvCleanerWidget()

    # Thử nghiệm: Bypass QFileDialog bằng cách gán cố định thư mục _external_folder
    target_folder = str(PROJECT_ROOT / "duchien")
    cleaner._external_folder = target_folder
    
    # ⚠️ Mẹo nhỏ: Vì select_and_process_files() thỉnh thoảng hiện QMessageBox, 
    # nên gán đè QMessageBox.information = pass (hoặc monkey-patch) nếu chạy cronjob 100% không người giám sát.
    # Trong môi trường test này, nếu chạy sẽ tạo ra duchien.csv và duchien.db
    
    try:
        # Nếu đã có file gộp duchien.csv từ trước, ta gọi đọc thẳng cho lẹ và đúng cấu trúc logic
        print(" -> Đang đọc file tổng hợp duchien.csv...")
        df_loaded = pd.read_csv(target_folder + "/duchien.csv")
        # Giả lập CsvCleanerWidget đã chạy xong:
        cleaner.df = df_loaded 
    except FileNotFoundError:
        print(" -> Không tìm thấy duchien.csv sẵn, đang build từ SQLite (chú ý: có thể hiện Popup của pyQt)...")
        cleaner.select_and_process_files()
        df_loaded = cleaner.df

    print(f" -> ✅ Đã load thành công DataFrame (shape: {df_loaded.shape})")


    # -------------------------------------------------------------------------
    # BƯỚC 2: CHẠY FORECASTING TỪ Forecasting_modules
    # -------------------------------------------------------------------------
    print("\n[BƯỚC 2] Khởi tạo ForecastingTab và phân tích dữ liệu...")
    
    # ForecastingTab cần một hàm provider để gọi lấy dataframe mỗi khi nó cần
    df_provider = lambda: df_loaded
    forecast_tab = ForecastingTab(df_provider=df_provider)
    
    # Kích hoạt sự kiện load data vào bên trong forecast_tab
    forecast_tab._load_data()

    # Setup Parameters từ code (Thay vì người dùng thao tác ở Settings Dialog)
    target_var = "AH O/L FG PRS"
    mw_var     = "NET MW"

    print(f" -> Cài đặt Target = '{target_var}', Load Filter = '{mw_var}' (>= 300 MW)")
    forecast_tab._target = target_var
    forecast_tab._input_vars = {mw_var}
    
    forecast_tab._settings = {
        "algo": "Polynomial Trend",
        "poly_degree": 2,          # Bậc 2
        "n_lag": 48,
        "ratio": 0.8,
        "mw_col": mw_var,
        "mw_min_threshold": 300.0, # Lọc bỏ máy ngừng / tải thấp
        "normalize_by_mw": False,
        "mw_ref": 600.0,
        "wash_threshold": -4.0,    # Ngưỡng vệ sinh tuỳ chỉnh
        "horizon": 720,            # Số bước dự báo tương lai
    }

    # Bắt đầu gọi method chạy thuật toán (y hệt như khi bấm nút Play)
    print(" -> Khởi chạy hàm Forecasting nội bộ (_run_stat_trend)...")
    try:
        # Phương thức này sẽ tính toán và hiện lên QWebEngineView nội bộ của Widget
        forecast_tab._run_stat_trend(method="poly")
        print(" -> ✅ Chạy dự báo thành công (Model đã tính xong MAE/RMSE/R2).")
        
        # Đọc ngược lại kết quả giao diện từ class
        print("\n📈 [KẾT QUẢ TỪ WIDGET UI]")
        print(" - MAE :", forecast_tab._card_mae._lbl_value.text())
        print(" - RMSE:", forecast_tab._card_rmse._lbl_value.text())
        print(" - Wash point:", forecast_tab._card_wash._lbl_value.text())

    except Exception as e:
        import traceback
        print(f" -> ❌ Lỗi khi chạy forecast: {e}")
        traceback.print_exc()

    print("\n✅ HOÀN TẤT AUTOMATION SCRIPT!")
    print("=" * 60)
    
if __name__ == "__main__":
    run_automation()
