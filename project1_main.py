import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QScrollArea, QPushButton, QLabel,
    QTabWidget, QTextEdit
)
from PySide6.QtWidgets import QMenu
from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import Qt
from project1_main_tab.load_data import CsvCleanerWidget
# from project1_main_tab.plot_tab import PlotTab
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from project1_main_tab.drift_tab import DriftMonitorTab
from project1_main_tab.predict_tab import PredictTab
from project1_main_tab.analysis_report_tab import AnalysisReportTab
from project1_main_tab.plotly_tab import PlotlyTab
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel, QHBoxLayout, QWidget, QSizePolicy
from ML_TAB.tabs.ml_application_tab import MLApplicationTab
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
from LtdViewerPy.main import MainWindow as LtdViewerWindow


def app_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Preview and analyze DataFrames")
        self.setGeometry(100, 100, 1000, 600)

        # === Layout chính
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setCentralWidget(main_widget)

        # === Scroll Area bên trái
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedWidth(180)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scroll_content.customContextMenuRequested.connect(self.show_folder_context_menu)

        self.scroll_content.setStyleSheet("background: #afcbff;")

        # ===== Thêm ô tìm kiếm folder
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Tìm folder...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setStyleSheet("""
            QLineEdit {
    background-color: #1a1c29;
    color: #e0e3f0;
    border: 1px solid #2a2e45;
    border-radius: 5px;
    padding-left: 10px;
    font-size: 14px;
    margin-bottom: 8px;
}
QLineEdit:hover {
    border: 1.2px solid #00bcd4;
}
QLineEdit:focus {
    border: 1.5px solid #8c5eff;
    background-color: #0f111a;
}

        """)
        self.search_box.textChanged.connect(self.on_search_folder)
        self.scroll_layout.addWidget(self.search_box)
        self.btn_load_data = QPushButton("📂 Load Data")
        self.btn_load_data.setFixedHeight(36)
        self.search_box.setMaximumWidth(150)
        self.btn_load_data.setMaximumWidth(150)

        self.btn_load_data.setStyleSheet("""
            QPushButton {
    background-color: #1a1c29;
    color: #00bcd4;
    border: 1px solid #2a2e45;
    border-radius: 6px;
    font-weight: bold;
    font-size: 13px;
    margin-bottom: 10px;
    padding: px 20px;
    min-height: 17px;


}
QPushButton:hover {
    background-color: #1d2b4f;
    color: #8c5eff;
    border: 1px solid #8c5eff;
}
QPushButton:pressed {
    background-color: #8c5eff;
    color: #0f111a;
    border: 1px solid #00bcd4;
}

        """)
        self.btn_load_data.clicked.connect(self.load_data_clicked)
        self.scroll_layout.addWidget(self.btn_load_data)

        self.btn_load_ltdt = QPushButton("📟 Load LTDT")
        self.btn_load_ltdt.setFixedHeight(36)
        self.btn_load_ltdt.setMaximumWidth(150)
        self.btn_load_ltdt.setStyleSheet(self.btn_load_data.styleSheet())
        self.btn_load_ltdt.clicked.connect(self.on_load_ltdt_clicked)
        self.scroll_layout.addWidget(self.btn_load_ltdt)

        # === Date format combobox - ngay dưới nút Load Data ===
        date_row = QWidget(self.scroll_content)
        date_row_layout = QHBoxLayout(date_row)
        date_row_layout.setContentsMargins(4, 0, 4, 0)
        date_row_layout.setSpacing(4)

        lbl_date_fmt = QLabel("Format:")
        lbl_date_fmt.setObjectName("lblDateFormat")

        self.cb_date_format = QComboBox(date_row)
        self.cb_date_format.setObjectName("cbDateFormat")

        self.cb_date_format.addItem(
            "dd/MM/yyyy",
            {"dayfirst": True, "fmt": "%d/%m/%Y %H:%M:%S"}
        )
        self.cb_date_format.addItem(
            "MM/dd/yyyy",
            {"dayfirst": False, "fmt": "%m/%d/%Y %I:%M:%S %p"}
        )

        self.cb_date_format.setCurrentIndex(0)
        self.cb_date_format.setFixedWidth(90)
        date_row.setMaximumWidth(150)  


        date_row_layout.addWidget(lbl_date_fmt)
        date_row_layout.addWidget(self.cb_date_format)
        date_row_layout.addStretch(1)

        self.scroll_layout.addWidget(date_row, 0, Qt.AlignLeft)


        self.load_folders()
        self.scroll_area.setWidget(self.scroll_content)


        # === Tab Widget bên phải
        self.tab_widget = QTabWidget()
        self.add_tabs()

        # === Ghép layout
        main_layout.addWidget(self.scroll_area, 1)
        main_layout.addWidget(self.tab_widget, 2)
        self.final_df = None
        self.data_manager = None

    def show_folder_context_menu(self, pos):
        global_pos = self.scroll_content.mapToGlobal(pos)
        menu = QMenu()
        refresh_action = menu.addAction("🔄 Refresh")
        action = menu.exec(global_pos)
        if action == refresh_action:
            filter_text = self.search_box.text()
            self.load_folders(filter_text)

    def set_final_df(self, df, folder_name="MergedData", data_manager=None):
        if not hasattr(self, "dataframes"):
            self.dataframes = {}
        self.dataframes[folder_name] = df
        self.final_df = df
        self.current_folder_name = folder_name
        if data_manager is not None:
            self.data_manager = data_manager
        if hasattr(self, "tab2"):
            self.tab2.update_variables(df)
        if hasattr(self, "drift_tab"):
            self.drift_tab.update_variables(df)
        if hasattr(self, "predict_tab"):
            self.predict_tab.update_variables(df)
        if hasattr(self, "analysis_report_tab"):
            self.analysis_report_tab.set_dataframe(df)
        if hasattr(self, "plotly_tab"):
            self.plotly_tab.update_plot(df)
        # Inject vào Monitoring nếu HTML đang hiển thị đúng folder
        folder = getattr(self, "_current_monitoring_folder", None)
        if folder and folder == folder_name and folder in self.MONITORING_COL_MAP:
            self._inject_monitoring_data(folder)

    def get_current_df_for_ml(self):
        """
        Hàm cung cấp DataFrame cho MLApplicationTab.
        Ở đây dùng final_df (dữ liệu đã xử lý ở Tab1).
        """
        return getattr(self, "final_df", None)

    def get_data_manager(self):
        """Trả về DataManager để query dữ liệu lớn theo time range / column selection."""
        return getattr(self, "data_manager", None)



    def get_df_list(self):
        if hasattr(self, "dataframes"):
            return [f"{k} (rows: {len(v)})" for k, v in self.dataframes.items()]
        return []

    def get_df_by_name(self, name: str):
        if hasattr(self, "dataframes") and name in self.dataframes:
            return self.dataframes[name]
        if name.startswith("MergedData"):
            return self.final_df
        return None



    def load_data_clicked(self):
        if hasattr(self, "csv_cleaner_widget"):
            self.csv_cleaner_widget.select_and_process_files_from_filelist()
            self.tab_widget.setCurrentIndex(0)

    def on_load_ltdt_clicked(self):
        if not hasattr(self, '_ltd_win') or not self._ltd_win.isVisible():
            self._ltd_win = LtdViewerWindow()
        self._ltd_win.show()
        self._ltd_win.raise_()

    def on_search_folder(self, text):
        self.load_folders(filter_text=text)

    def load_folders(self, filter_text=""):
        # Xóa các widget cũ (trừ ô tìm kiếm + nút Load Data + date_row)
        for i in reversed(range(3, self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            w = item.widget()
            if w is not None:
                w.setParent(None)
            else:
                self.scroll_layout.removeItem(item)

        INTERNAL_FOLDERS = {
            "Monitoring storage",
            "formulas",
            "__pycache__",
            ".git",
            ".idea",
            ".vscode",
            "_internal",
            "build",
            "dist",
            "logs",
            "Temp",
            "csv_archive",
        }

        base_path = app_dir()
        matched_count = 0
        ft = (filter_text or "").lower().strip()

        for folder in sorted(base_path.iterdir()):
            if not folder.is_dir():
                continue

            name = folder.name

            # 1) bỏ qua folder nội bộ + folder bắt đầu bằng "."
            if name.startswith(".") or name in INTERNAL_FOLDERS:
                continue

            # 2) filter search
            if ft and ft not in name.lower():
                continue

            btn = QPushButton(name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 12px;
                    background-color: transparent;
                    color: #000000;
                    font-weight: bold;
                    border: none;
                    border-radius: 5px;
                    margin-bottom: 4px;
                }
                QPushButton:hover {
                    background-color: #cce5ff;
                    color: #004a99;
                }
            """)
            btn.clicked.connect(lambda _, n=name: self.open_folder(n))
            self.scroll_layout.addWidget(btn)
            matched_count += 1

        if matched_count > 0:
            self.scroll_layout.addStretch()


    # Mapping cột DataFrame → thứ tự mảng D cho từng HTML
    # Thêm folder mới vào đây khi có HTML tương ứng
    MONITORING_COL_MAP = {
        "AH_U2": [
            "NET MW", "ECO O/L FG TEMP", "AH O/L FG TEMP",
            "AH I/L PA TEMP", "AH O/L PA TEMP",
            "AH I/L SECAIR TEMP", "AH O/L SECAIR TEMP",
            "ECO O/L FG ANALR 1 PRB O2 DNSTY 1 VLU",
            "ECO O/L FG ANALR 1 PRB O2 DNSTY 2 VLU",
            "ECO O/L FG ANALR 2 PRB O2 DNSTY 1 VLU",
            "ECO O/L FG ANALR 2 PRB O2 DNSTY 2 VLU",
            "AH RTDRV CURR", "AH GDBRG TEMP", "AH SPT BRG TEMP",
            "AH SECAIR BYP CDPR CDRV POSN FDBK",
            "ECO O/L FG PRS", "AH O/L FG PRS",
            "PAF A O/L AIR PRS", "PAF B O/L AIR PRS",
            "HPA PRS SETP BIAS PV",
            "FDF A O/L AIR PRS", "FDF B O/L AIR PRS",
            "AH O/L SECAIR PRS",
            "AH SOOTBLOWER HOT SIDE RETRACTED",
            "AH SOOTBLOWER COLD SIDE RETRACTED",
        ],
        "U2-Main_Turbine": [],
    }

    def open_folder(self, folder_name):
        folder_path = app_dir() / folder_name
        if hasattr(self, "csv_cleaner_widget"):
            self.csv_cleaner_widget._external_folder = str(folder_path)
            self.csv_cleaner_widget.select_and_process_files()
            self.tab_widget.setCurrentIndex(0)
        self._current_monitoring_folder = folder_name
        self._load_monitoring_for_folder(folder_name)

    def _load_monitoring_placeholder(self):
        html = """
        <html><body style="margin:0;display:flex;align-items:center;justify-content:center;
                           height:100vh;background:#1a1c29;color:#4a4e6a;font-family:sans-serif;">
            <div style="text-align:center">
                <div style="font-size:48px;margin-bottom:16px">📡</div>
                <div style="font-size:16px">Chọn folder dữ liệu để hiển thị giao diện giám sát</div>
            </div>
        </body></html>
        """
        self.monitoring_web_view.setHtml(html)

    def _load_monitoring_for_folder(self, folder_name):
        if not hasattr(self, "monitoring_web_view"):
            return
        html_path = app_dir() / "Systems" / f"{folder_name}.html"
        if html_path.exists():
            # Ngắt kết nối signal cũ nếu có
            try:
                self.monitoring_web_view.loadFinished.disconnect()
            except RuntimeError:
                pass
            # Kết nối inject data sau khi HTML load xong
            if folder_name in self.MONITORING_COL_MAP:
                self.monitoring_web_view.loadFinished.connect(
                    lambda *_, fn=folder_name: self._inject_monitoring_data(fn)
                )
            self.monitoring_web_view.load(QUrl.fromLocalFile(str(html_path.resolve())))
        else:
            html = f"""
            <html><body style="margin:0;display:flex;align-items:center;justify-content:center;
                               height:100vh;background:#1a1c29;color:#4a4e6a;font-family:sans-serif;">
                <div style="text-align:center">
                    <div style="font-size:48px;margin-bottom:16px">📡</div>
                    <div style="font-size:16px">Chưa có giao diện giám sát cho <b style="color:#8c5eff">{folder_name}</b></div>
                    <div style="font-size:12px;margin-top:8px;color:#333">
                        Tạo file: <code style="color:#00bcd4">Systems/{folder_name}.html</code>
                    </div>
                </div>
            </body></html>
            """
            self.monitoring_web_view.setHtml(html)

    def _inject_monitoring_data(self, folder_name):
        """Chuyển DataFrame → mảng D rồi gọi onDataReady() trong HTML."""
        import json
        import math

        df = getattr(self, "final_df", None)
        if df is None or df.empty:
            return
        cols = self.MONITORING_COL_MAP.get(folder_name)
        if not cols:
            return

        rows = []
        for _, row in df.iterrows():
            dt_str = str(row["Datetime"])[:19]  # "YYYY-MM-DD HH:MM:SS"
            r = [dt_str]
            for col in cols:
                val = row.get(col, 0)
                try:
                    v = float(val)
                    r.append(0 if math.isnan(v) else round(v, 3))
                except (TypeError, ValueError):
                    r.append(0)
            rows.append(r)

        data_json = json.dumps(rows)
        js = f"if(typeof onDataReady==='function') onDataReady({data_json});"
        self.monitoring_web_view.page().runJavaScript(js)

    def add_tabs(self):
        tab1 = QWidget()
        layout1 = QVBoxLayout(tab1)
        layout1.setContentsMargins(0, 0, 0, 0)
        layout1.setSpacing(0)

        # Inner tab widget bên trong Home
        self.inner_tab_widget = QTabWidget()

        # Tab con 1: Draw Data - chứa bảng dữ liệu thô
        self.csv_cleaner_widget = CsvCleanerWidget(parent_main_window=self)
        self.inner_tab_widget.addTab(self.csv_cleaner_widget, "📋 Draw Data")

        # Tab con 2: Monitoring - WebView hiển thị HTML hệ thống
        self.monitoring_web_view = QWebEngineView()
        self._load_monitoring_placeholder()
        self.inner_tab_widget.addTab(self.monitoring_web_view, "📡 Monitoring")

        layout1.addWidget(self.inner_tab_widget)
        self.tab_widget.addTab(tab1, "🏠 Home")

        # Tab 2 - Plot
        # self.tab2 = PlotTab(parent=self)
        # self.tab_widget.addTab(self.tab2, "📈 Plot")
        # Tab 6 - Plotly
        self.plotly_tab = PlotlyTab(parent=self)
        self.tab_widget.addTab(self.plotly_tab, "🌐 Plotly")

        # Tab 3 - Drift Monitor
        self.drift_tab = DriftMonitorTab(parent=self)
        self.tab_widget.addTab(self.drift_tab, "🔄 Drift Monitor")
        # Tab 4 - Predict   
        self.predict_tab = PredictTab(parent=self)
        self.tab_widget.addTab(self.predict_tab, "🔮 Predict")
        # Tab 5 - Analysis Report
        self.analysis_report_tab = AnalysisReportTab(parent=self)
        self.tab_widget.addTab(self.analysis_report_tab, "📊 Analysis Report")

