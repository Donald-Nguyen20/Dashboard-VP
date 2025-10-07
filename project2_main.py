# project2_main.py

from pathlib import Path
import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QScrollArea, QPushButton, QLabel, QTabWidget, QLineEdit
)
from PySide6.QtCore import Qt

def app_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

class SystemMonitoringWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Monitoring")
        self.setGeometry(100, 100, 1000, 600)

        # Layout chính
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # Scroll Area bên trái
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedWidth(180)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        search_box = QLineEdit()
        search_box.setPlaceholderText("🔍 Search System...")
        scroll_layout.addWidget(search_box)

        sample_button = QPushButton("⏱ CPU Monitor")
        scroll_layout.addWidget(sample_button)

        scroll_content.setLayout(scroll_layout)
        self.scroll_area.setWidget(scroll_content)

        # Tab Widget bên phải
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(QLabel("📡 System Overview..."), "Overview")
        self.tab_widget.addTab(QLabel("⚙ Logs & Status..."), "Logs")

        # Ghép 2 phần vào main layout
        main_layout.addWidget(self.scroll_area, 1)
        main_layout.addWidget(self.tab_widget, 2)
