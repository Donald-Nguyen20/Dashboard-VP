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

    def show_folder_context_menu(self, pos):
        global_pos = self.scroll_content.mapToGlobal(pos)
        menu = QMenu()
        refresh_action = menu.addAction("🔄 Refresh")
        action = menu.exec(global_pos)
        if action == refresh_action:
            filter_text = self.search_box.text()
            self.load_folders(filter_text)

    def set_final_df(self, df, folder_name="MergedData"):
        if not hasattr(self, "dataframes"):
            self.dataframes = {}
        self.dataframes[folder_name] = df
        self.final_df = df
        self.current_folder_name = folder_name
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

    def get_current_df_for_ml(self):
        """
        Hàm cung cấp DataFrame cho MLApplicationTab.
        Ở đây dùng final_df (dữ liệu đã xử lý ở Tab1).
        """
        return getattr(self, "final_df", None)



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

    def on_search_folder(self, text):
        self.load_folders(filter_text=text)

    def load_folders(self, filter_text=""):
        # Xóa các widget cũ (trừ ô tìm kiếm)
        for i in reversed(range(3, self.scroll_layout.count())):

            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
            else:
                item = self.scroll_layout.itemAt(i)
                self.scroll_layout.removeItem(item)

        base_path = app_dir()
        matched_count = 0
        for folder in sorted(base_path.iterdir()):
            if folder.is_dir() and not folder.name.startswith('.'):
                if filter_text.lower() not in folder.name.lower():
                    continue
                btn = QPushButton(f"{folder.name}")
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
                btn.clicked.connect(lambda _, name=folder.name: self.open_folder(name))
                self.scroll_layout.addWidget(btn)
                matched_count += 1
        if matched_count > 0:
            self.scroll_layout.addStretch()


    def open_folder(self, folder_name):
        folder_path = app_dir() / folder_name
        if hasattr(self, "csv_cleaner_widget"):
            self.csv_cleaner_widget._external_folder = str(folder_path)
            self.csv_cleaner_widget.select_and_process_files()
            self.tab_widget.setCurrentIndex(0)

    def add_tabs(self):
        tab1 = QWidget()
        layout1 = QVBoxLayout(tab1)
        layout1.setContentsMargins(0, 0, 0, 0)
        layout1.setSpacing(0)

        self.csv_cleaner_widget = CsvCleanerWidget(parent_main_window=self)
        layout1.addWidget(self.csv_cleaner_widget)
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

