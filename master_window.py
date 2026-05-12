# master_window.py

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QPushButton
from PySide6.QtGui import QKeySequence, QShortcut
from project1_main import MainWindow
from ML_TAB.windows.ML_tab import ML_Tab
from Monitoring.windows.monitoring_tab import Monitoring_Tab
from help_dialog import HelpDialog

"""pyinstaller --onedir --name master_window --icon DFA.ico --exclude-module tkinter --exclude-module PyQt5 --exclude-module torch --add-data "ML_TAB\assets;ML_TAB\assets" master_window.py
"""
def app_dir():
    """
    Trả về thư mục chứa file .exe khi đóng gói,
    hoặc thư mục chứa file master_window.py khi debug.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

def apply_theme(app):
    stylesheet = """
/* ================================================================
   DASHBOARD THEME — Light Blue Professional
   Màu chủ đạo : #2f6fe4 (xanh dương)
   Nền          : #f0f4fb (xanh nhạt trung tính)
   Surface      : #ffffff (trắng thuần — bảng, input, dialog)
================================================================ */

/* ==== BASE ==== */
QWidget {
    background-color: #f0f4fb;
    color: #1e2a36;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #e8eef8;
}

QLabel {
    background: transparent;
    color: #1e2a36;
}

/* ==== TAB WIDGET ==== */
QTabWidget::pane {
    border: 1.5px solid #b8ccec;
    background-color: #f8fbff;
    border-radius: 0 8px 8px 8px;
    top: -1px;
}

QTabBar::tab {
    background-color: #dde8f8;
    color: #4a6080;
    padding: 9px 24px;
    border: 1.5px solid #b8ccec;
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    margin-right: 3px;
    font-weight: 500;
}

QTabBar::tab:hover {
    background-color: #c8d8f5;
    color: #1e3c78;
}

QTabBar::tab:selected {
    background-color: #2f6fe4;
    color: white;
    font-weight: bold;
    border-color: #2f6fe4;
}

/* ==== BUTTON ==== */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #e4eeff);
    color: #1b3a6e;
    border: 1px solid #aabfdc;
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 28px;
    font-weight: 500;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #5a9bf0, stop:1 #2f6fe4);
    color: white;
    border: 1px solid #1a5cbf;
}

QPushButton:pressed {
    background-color: #1a5cbf;
    color: white;
    border: 1px solid #0f3f8a;
}

QPushButton:disabled {
    background-color: #d8e4f0;
    color: #8fa8c8;
    border: 1px solid #c0d0e4;
}

/* ==== TOOLBAR ==== */
QToolBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ccdff8, stop:1 #a0c0f0);
    border-bottom: 2px solid #2f6fe4;
    padding: 4px;
    spacing: 4px;
}

/* ==== TOOLBUTTON ==== */
QToolButton {
    background-color: #ddeafc;
    color: #1b2a38;
    border: 1px solid #aabfdc;
    border-radius: 6px;
    font-weight: 500;
    padding: 5px 12px;
    min-height: 28px;
}

QToolButton:hover {
    background-color: #2f6fe4;
    color: white;
    border: 1px solid #2f6fe4;
}

QToolButton:pressed, QToolButton:checked {
    background-color: #1a5cbf;
    color: white;
}

QToolButton::menu-indicator { image: none; }

QToolButton::menu-button {
    background-color: transparent;
    border-left: 1px solid #aabfdc;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    width: 18px;
}

/* ==== TABLE ==== */
QTableView, QTableWidget {
    background-color: #ffffff;
    gridline-color: #dce8ff;
    selection-background-color: #4a8fe8;
    selection-color: white;
    alternate-background-color: #f3f8ff;
    border: 1.5px solid #b8ccec;
    border-radius: 6px;
}

QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #dce8ff, stop:1 #b0cbf5);
    color: #1e3c78;
    border: none;
    border-right: 1px solid #b8ccec;
    border-bottom: 2px solid #2f6fe4;
    font-weight: bold;
    padding: 6px 8px;
}

QHeaderView::section:hover { background-color: #c4d8f8; }

/* ==== INPUT ==== */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: white;
    border: 1.5px solid #b8ccec;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1e2a36;
    selection-background-color: #4a8fe8;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #2f6fe4;
    background-color: #fdfeff;
}

QLineEdit:disabled, QTextEdit:disabled {
    background-color: #edf2fa;
    color: #8fa8c8;
    border-color: #cdd8ec;
}

/* ==== COMBOBOX ==== */
QComboBox {
    background-color: white;
    border: 1.5px solid #b8ccec;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1e2a36;
    min-width: 80px;
}

QComboBox:hover { border: 1.5px solid #4a8fe8; }
QComboBox:focus { border: 2px solid #2f6fe4; }
QComboBox::drop-down { border: none; width: 24px; }

QComboBox QAbstractItemView {
    background-color: white;
    border: 1.5px solid #b8ccec;
    border-radius: 6px;
    selection-background-color: #4a8fe8;
    selection-color: white;
    padding: 2px;
}

/* ==== SPINBOX ==== */
QSpinBox, QDoubleSpinBox, QDateTimeEdit {
    background-color: white;
    border: 1.5px solid #b8ccec;
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 32px;
    color: #1e2a36;
}

QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus {
    border: 2px solid #2f6fe4;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #e4eeff;
    border: none;
    border-left: 1px solid #b8ccec;
    width: 18px;
    border-radius: 3px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #4a8fe8;
}

/* ==== CHECKBOX ==== */
QCheckBox { spacing: 8px; color: #1e2a36; }

QCheckBox::indicator {
    width: 17px; height: 17px;
    border-radius: 4px;
    border: 2px solid #aabfdc;
    background-color: white;
}

QCheckBox::indicator:hover { border: 2px solid #2f6fe4; }
QCheckBox::indicator:checked { background-color: #2f6fe4; border: 2px solid #2f6fe4; }

/* ==== RADIO BUTTON ==== */
QRadioButton { spacing: 8px; color: #1e2a36; }

QRadioButton::indicator {
    width: 17px; height: 17px;
    border-radius: 9px;
    border: 2px solid #aabfdc;
    background-color: white;
}

QRadioButton::indicator:hover { border: 2px solid #2f6fe4; }
QRadioButton::indicator:checked { background-color: #2f6fe4; border: 5px solid white; }

/* ==== SCROLLBAR ==== */
QScrollBar:vertical {
    background-color: #edf2fb; width: 10px; border-radius: 5px; margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #a8c0e0; border-radius: 5px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: #4a8fe8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background-color: #edf2fb; height: 10px; border-radius: 5px; margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #a8c0e0; border-radius: 5px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background-color: #4a8fe8; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ==== MENU ==== */
QMenu {
    background-color: #f4f8ff; color: #1b2a38;
    border: 1px solid #b8ccec; border-radius: 8px;
    font-weight: 500; padding: 4px 0;
}
QMenu::item { background: transparent; padding: 8px 24px; border-radius: 4px; margin: 1px 4px; }
QMenu::item:selected { background-color: #4a8fe8; color: white; }
QMenu::item:disabled { color: #8fa8c8; }
QMenu::separator { height: 1px; background-color: #c8d8f0; margin: 4px 8px; }

/* ==== MENUBAR ==== */
QMenuBar {
    background-color: #d0e0f8; color: #1b2a38;
    border-bottom: 1px solid #aabfdc; padding: 2px;
}
QMenuBar::item { padding: 6px 12px; border-radius: 4px; }
QMenuBar::item:selected { background-color: #4a8fe8; color: white; }

/* ==== GROUP BOX ==== */
QGroupBox {
    font-weight: bold; font-size: 13px; color: #1e3c78;
    border: 1.5px solid #b8ccec; border-radius: 8px;
    margin-top: 14px; padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 12px; padding: 0 6px;
    color: #2f6fe4; background-color: #f0f4fb;
}

/* ==== PROGRESS BAR ==== */
QProgressBar {
    background-color: #dce8ff; border: 1px solid #b8ccec;
    border-radius: 6px; height: 12px;
    text-align: center; color: #1e2a36; font-size: 11px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5a9bf0, stop:1 #2f6fe4);
    border-radius: 5px;
}

/* ==== SPLITTER ==== */
QSplitter::handle { background-color: #c0d4f0; }
QSplitter::handle:horizontal { width: 4px; }
QSplitter::handle:vertical { height: 4px; }
QSplitter::handle:hover { background-color: #4a8fe8; }

/* ==== STATUS BAR ==== */
QStatusBar {
    background-color: #d0e0f8; color: #1b2a38;
    border-top: 1px solid #aabfdc; font-size: 12px;
}

/* ==== LIST / TREE ==== */
QListView, QTreeView {
    background-color: white; border: 1.5px solid #b8ccec;
    border-radius: 6px;
    selection-background-color: #4a8fe8; selection-color: white;
    alternate-background-color: #f3f8ff;
}
QListView::item:hover, QTreeView::item:hover { background-color: #ddeafc; }
QListView::item:selected, QTreeView::item:selected { background-color: #4a8fe8; color: white; }

/* ==== TOOLTIP ==== */
QToolTip {
    background-color: #1e2a36; color: #e8f0fc;
    border: 1px solid #4a8fe8; border-radius: 5px;
    padding: 5px 9px; font-size: 12px;
}

/* ==== FRAME LINES ==== */
QFrame[frameShape="4"], QFrame[frameShape="5"] { color: #c0d4f0; }
    """
    app.setStyleSheet(stylesheet)

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

        # Phím F1 mở hướng dẫn sử dụng
        QShortcut(QKeySequence("F1"), self, activated=self._open_help)

    def _open_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def add_new_project_tab(self):
        main_window = MainWindow()
        widget = main_window.centralWidget()
        index = self.tab_widget.addTab(widget, f"📁 Project {self.tab_widget.count() + 1}")
        self.tab_widget.setCurrentIndex(index)

if __name__ == "__main__":
    os.chdir(app_dir())
    app = QApplication(sys.argv)
    apply_theme(app)
    window = MasterWindow()
    window.showMaximized()
    sys.exit(app.exec())
    