# master_window.py

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QPushButton
from project1_main import MainWindow
from ML_TAB.windows.ML_tab import ML_Tab
from Monitoring.windows.monitoring_tab import Monitoring_Tab


def app_dir():
    """
    Trả về thư mục chứa file .exe khi đóng gói,
    hoặc thư mục chứa file master_window.py khi debug.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

def apply_dark_theme(app):
    dark_stylesheet = """
/* ==== GLOBAL ==== */
QWidget { 
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #f8fbff,
        stop:0.4 #eef5ff,
        stop:1 #dce9ff
    );
    color: #1e2a36;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 14px;
}

/* ==== TAB WIDGET ==== */
QTabWidget::pane {
    border: 1px solid #c7d6ea;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #f3f8ff,
        stop:1 #dbe8ff
    );
    border-radius: 10px;
}

QTabBar::tab {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #e8f2ff,
        stop:1 #c6dbff
    );
    color: #405168;
    padding: 8px 22px;
    border-radius: 10px 10px 0 0;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #7fb3ff,
        stop:1 #2f6fe4
    );
    color: white;
    font-weight: bold;
}

/* ==== BUTTON ==== */
QPushButton {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #f4f9ff,
        stop:1 #d7e9ff
    );
    color: #1b2a38;
    border: 1px solid #b6c7d8;
    border-radius: 8px;
    padding: 7px 18px;
    font-weight: 500;
}

QPushButton:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #7fb3ff,
        stop:1 #2f6fe4
    );
    color: white;
    border: 1px solid #2f6fe4;
}

/* ==== TOOLBAR ==== */
QToolBar {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #cfe3ff,
        stop:1 #9ec5ff
    );
    border-bottom: 2px solid #2f6fe4;
}

/* ==== TABLE ==== */
QTableView {
    background-color: #f9fbff;
    gridline-color: #dbe8ff;
    selection-background-color: #5f9cff;
    selection-color: white;
    alternate-background-color: #edf4ff;
}

QHeaderView::section {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #dbe8ff,
        stop:1 #a9c9ff
    );
    color: #1e3c78;
    border: 1px solid #b6c7d8;
    font-weight: bold;
    padding: 5px;
}

/* ==== INPUT ==== */
QLineEdit, QTextEdit, QComboBox, QDateTimeEdit {
    background: white;
    border: 1.5px solid #c7d6ea;
    border-radius: 6px;
    padding: 6px 12px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 2px solid #2f6fe4;
}

/* ==== CHECKBOX ==== */
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #2f6fe4;
    background: white;
}

QCheckBox::indicator:checked {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #7fb3ff,
        stop:1 #2f6fe4
    );
}

/* ==== MENU ==== */
QMenu {
    background: #f4f9ff;
    border: 1px solid #c7d6ea;
    border-radius: 8px;
}

QMenu::item:selected {
    background: #5f9cff;
    color: white;
}

/* ==== MENU ==== */
QMenu {
    background-color: #e0ecff;
    color: #1b2a38;
    border: 1.2px solid #b6c7d8;
    border-radius: 6px;
    font-weight: 500;
    padding: 6px 0;
}
QMenu::item {
    background: transparent;
    padding: 8px 20px;
}
QMenu::item:selected {
    background: #cde0fd;
    color: #0057b8;
}

/* ==== TOOLBUTTON ==== */
QToolButton {
    background: #e0ecff;
    color: #1b2a38;
    border: 1.2px solid #b6c7d8;
    border-radius: 6px;
    font-weight: 500;
    padding: 5px 12px;
}
QToolButton::menu-indicator {
    image: none;
    background: #e0ecff;
    border-left: 1.2px solid #b6c7d8;
    width: 20px;
}
QToolButton::menu-button {
    background: #e0ecff;
    border-left: 1.2px solid #b6c7d8;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}
QToolButton:pressed, QToolButton:checked {
    background: #d0e7ff;
}
QToolButton:hover {
    background: #cde0fd;
    color: #0057b8;
    border: 1.5px solid #245cb6;
}
    """
    app.setStyleSheet(dark_stylesheet)

class MasterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧠 Multi Project Dashboard")
        self.setGeometry(50, 50, 1280, 800)

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Giữ tham chiếu main_window để df_provider luôn truy cập được final_df
        self.main_window = MainWindow()
        widget = self.main_window.centralWidget()
        self.tab_widget.addTab(widget, "📊 Data Analyzing")

        # Tab 2: ML Application (từ windows/ML_tab.py)
        ml_win = ML_Tab(df_provider=self.main_window.get_current_df_for_ml)
        ml_widget = ml_win.centralWidget()
        ml_widget.setStyleSheet(ml_win.styleSheet())
        self.tab_widget.addTab(ml_widget, "🤖 ML Application")

        # Tab 3: Monitoring System (Get Plot lấy đồ thị từ tab Plotly - cùng cách thức như Plot: figure → ảnh)
        monitoring_win = Monitoring_Tab(
            df_provider=self.main_window.get_current_df_for_ml,
            plot_provider=lambda: getattr(self.main_window, "plotly_tab", None),
        )
        monitoring_widget = monitoring_win.centralWidget()
        self.tab_widget.addTab(monitoring_widget, "📡 Monitoring System")

    def add_new_project_tab(self):
        main_window = MainWindow()
        widget = main_window.centralWidget()
        index = self.tab_widget.addTab(widget, f"📁 Project {self.tab_widget.count() + 1}")
        self.tab_widget.setCurrentIndex(index)

if __name__ == "__main__":
    os.chdir(app_dir())
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    window = MasterWindow()
    window.show()
    sys.exit(app.exec())
    