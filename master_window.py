# master_window.py

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QPushButton
from project1_main import MainWindow
from ML_TAB.windows.ML_tab import ML_Tab


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
QWidget { 
    background-color: #f5f7fa;
    color: #232b34;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 14px;
}

/* ==== TAB WIDGET ==== */
QTabWidget::pane {
    border: 1px solid #d0d7de;
    background: #eaf0f6;
}
QTabBar::tab {
    background: #dbe8f5;
    color: #405168;
    padding: 8px 20px 8px 20px;
    border-radius: 8px 8px 0 0;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #b8d3f4;
    color: #245cb6;
    font-weight: bold;
}

/* ==== SCROLL AREA ==== */
QScrollArea, QScrollBar:vertical {
    background: #afcbff; 
}

/* ==== BUTTON ==== */
QPushButton {
    background-color: #eaf0f6;
    color: #1b2a38;
    border: 1px solid #b6c7d8;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #d0e7ff;
    color: #245cb6;
    border: 1px solid #97b3d0;
}

/* ==== TEXT INPUT ==== */
QLineEdit, QTextEdit {
    background-color: #ffffff;
    color: #1b2a38;
    border: 1px solid #b6c7d8;
    border-radius: 5px;
}

/* ==== TABLE ==== */
QTableView {
    background-color: #f9fbfd;
    color: #1b2a38;
    gridline-color: #dbe8f5;
    selection-background-color: #cfe2f3;
    selection-color: #204080;
    alternate-background-color: #eaf3fb;
}
QHeaderView::section {
    background-color: #dbe8f5;
    color: #245cb6;
    border: 1px solid #b6c7d8;
    font-weight: bold;
    padding: 4px;
} 

/* ==== TOOLBAR ==== */
QToolBar {
    background: #e0ecff;
    border-bottom: 1.5px solid #b6c7d8;
}

/* ==== COMBOBOX & DATETIMEEDIT ==== */
QComboBox, QDateTimeEdit {
    background: #e0ecff;
    color: #1b2a38;
    border: 1.2px solid #b6c7d8;
    border-radius: 6px;
    font-weight: 500;
    padding: 5px 12px;
}
QComboBox:hover, QDateTimeEdit:hover {
    background: #cde0fd;
    color: #0057b8;
    border: 1.5px solid #245cb6;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    selection-background-color: #eaf0f6;
    color: #232b34;
}

/* ==== TOOLBAR BUTTON & COMBOBOX (RIÊNG TOOLBAR) ==== */
QToolBar QToolButton {
    background: #368de3;
    color: #fff;
    border: 1.2px solid #b6c7d8;
    border-radius: 6px;
    font-weight: 500;
    padding: 5px 12px;
}
QToolBar QToolButton:hover {
    background: #176fd9;
    color: #fff;
    border: 1.5px solid #245cb6;
}
QToolBar QComboBox {
    background: #e0ecff;
    color: #1b2a38;
    border: 1.2px solid #b6c7d8;
    border-radius: 6px;
    font-weight: 500;
    padding: 5px 12px;
}
QToolBar QComboBox:hover {
    background: #cde0fd;
    color: #0057b8;
    border: 1.5px solid #245cb6;
}

/* ==== CHECKBOX ==== */
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #222;
    border-radius: 4px;
    background: #fff;
    margin-right: 5px;
}
QCheckBox::indicator:unchecked {
    background: #fff;
    border: 2px solid #222;
}
QCheckBox::indicator:checked {
    background: #52a2fa;
    border: 2px solid #222;
}
QCheckBox::indicator:unchecked:hover, QCheckBox::indicator:checked:hover {
    background: #b8d3f4;
    border: 2px solid #0057b8;
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

        main_window = MainWindow()
        widget = main_window.centralWidget()
        self.tab_widget.addTab(widget, "📊 Data Analyzing")

        # Tab 2: ML Application (từ windows/ML_tab.py)
        ml_win = ML_Tab(df_provider=main_window.get_current_df_for_ml)
        ml_widget = ml_win.centralWidget()
        ml_widget.setStyleSheet(ml_win.styleSheet())
        self.tab_widget.addTab(ml_widget, "🤖 ML Application")

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
    