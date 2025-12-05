from __future__ import annotations
import os, sys
from PySide6.QtWidgets import QMainWindow, QTabWidget
from ML_TAB.tabs.ml_application_tab import MLApplicationTab


def resource_path(rel_path: str) -> str:
    """
    Tạo đường dẫn tương thích cả khi chạy bình thường lẫn khi build PyInstaller.
    rel_path ví dụ: "assets/qss/base.qss"
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(os.path.abspath(os.path.join(base, "..")), rel_path)


class ML_Tab(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ML Dashboard")
        self.resize(1400, 800)
        self.setObjectName("MLDashboardWindow")
        # Tabs chính
        tabs = QTabWidget(self)
        tabs.setTabPosition(QTabWidget.North)
        tabs.setDocumentMode(True)
        tabs.setTabsClosable(False)
        self.setCentralWidget(tabs)

        # Tab ML Application
        self.ml_tab = MLApplicationTab(self)
        tabs.addTab(self.ml_tab, "ML Application")

        # ✨ Nạp theme ngay tại đây (thay cho main.py cũ)
        self._apply_theme_from_files()

    def _apply_theme_from_files(self):
        """Đọc 2 file QSS (base + dark) và áp dụng."""
        here = os.path.dirname(os.path.abspath(__file__))          # .../ML APP/windows
        project_root = os.path.abspath(os.path.join(here, ".."))   # .../ML APP

        base_path  = os.path.join(project_root, "assets", "qss", "base.qss")
        theme_path = os.path.join(project_root, "assets", "qss", "dark.qss")

        def read_file(path: str) -> str:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            print(f"⚠️ Không tìm thấy file QSS: {path}")
            return ""

        base_css  = read_file(base_path)
        theme_css = read_file(theme_path)

        # Base trước, theme sau (theme override base nếu trùng selector)
        self.setStyleSheet(base_css + "\n" + theme_css)

        # Log ra console để anh dễ kiểm tra
        print(f"✔ Loaded base:  {base_path if os.path.exists(base_path) else 'N/A'}")
        print(f"✔ Loaded theme: {theme_path if os.path.exists(theme_path) else 'N/A'}")
