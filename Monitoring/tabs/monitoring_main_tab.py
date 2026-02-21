"""
Tab chính của Monitoring System.
Layout khoa học: panel trái (hệ thống + nút hành động), panel phải (bố cục hàng/cột + ô đồ thị/text).
"""
from __future__ import annotations
import uuid
from typing import Optional, Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QPushButton,
    QInputDialog,
    QMessageBox,
    QStackedWidget,
)
from PySide6.QtGui import QFont
from Monitoring.config.storage import (
    load_all_systems,
    save_all_systems,
    get_storage_dir,
    SystemConfig,
)
from Monitoring.widgets.system_content_widget import SystemContentWidget


_BTN_STYLE = """
    QPushButton {
        text-align: center;
        border-radius: 6px;
        font-weight: 500;
    }
    QPushButton:hover { border: 1.5px solid #245cb6; }
"""

_BTN_SAVE = """
    QPushButton {
        background-color: #28a745;
        color: #fff;
        border: 1px solid #1e7e34;
    }
    QPushButton:hover { background-color: #218838; }
    QPushButton:disabled { background-color: #6c757d; }
"""

_BTN_DELETE = """
    QPushButton {
        background-color: #dc3545;
        color: #fff;
        border: 1px solid #c82333;
    }
    QPushButton:hover { background-color: #c82333; }
    QPushButton:disabled { background-color: #6c757d; }
"""

_BTN_ADD = """
    QPushButton {
        background-color: #368de3;
        color: #fff;
        border: 1px solid #176fd9;
    }
    QPushButton:hover { background-color: #176fd9; }
"""


class MonitoringMainTab(QWidget):
    """
    Tab chính của Monitoring System.
    Cấu trúc: [Panel trái | Panel phải]
    - Panel trái: danh sách hệ thống, nút Add/Save/Delete
    - Panel phải: chi tiết hệ thống được chọn
    """
    def __init__(self, parent: Optional[QWidget] = None, df_provider: Callable[[], object] | None = None, plot_provider: Callable[[], object] | None = None):
        super().__init__(parent)
        self.setObjectName("MonitoringMainTab")
        self.df_provider = df_provider or (lambda: None)
        self.plot_provider = plot_provider or (lambda: None)
        self.systems: list[SystemConfig] = []
        self.current_system: Optional[SystemConfig] = None
        self._dirty = False  # có thay đổi chưa lưu

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ─── Panel trái: Hệ thống giám sát ───────────────────────────
        left = QFrame()
        left.setObjectName("monitoringLeftPanel")
        left.setFixedWidth(260)
        left.setFrameShape(QFrame.StyledPanel)
        left.setStyleSheet("""
            #monitoringLeftPanel {
                background: #eaf0f6;
                border-right: 1px solid #b6c7d8;
            }
        """)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        # Tiêu đề
        lbl = QLabel("Hệ thống giám sát")
        lbl.setStyleSheet("font-weight: bold; color: #1b2a38; font-size: 14px;")
        left_layout.addWidget(lbl)

        # Nhóm nút hành động
        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(8)
        self.btn_add = QPushButton("➕ Tạo mới")
        self.btn_add.setFixedHeight(38)
        self.btn_add.setStyleSheet(_BTN_ADD + _BTN_STYLE)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self._on_add)
        btn_row1.addWidget(self.btn_add)
        left_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(8)
        self.btn_save = QPushButton("💾 Save")
        self.btn_save.setFixedHeight(38)
        self.btn_save.setStyleSheet(_BTN_SAVE + _BTN_STYLE)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save.setEnabled(False)
        btn_row2.addWidget(self.btn_save)

        self.btn_delete = QPushButton("🗑️ Delete")
        self.btn_delete.setFixedHeight(38)
        self.btn_delete.setStyleSheet(_BTN_DELETE + _BTN_STYLE)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_delete.setEnabled(False)
        btn_row2.addWidget(self.btn_delete)
        left_layout.addLayout(btn_row2)

        # Danh sách hệ thống (scrollable)
        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent;")
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 4, 0, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_container)
        left_layout.addWidget(self.scroll, 1)

        # Ghi chú storage
        storage_path = get_storage_dir()
        lbl_storage = QLabel(f"📁 Lưu tại: {storage_path.name}/")
        lbl_storage.setStyleSheet("color: #6c757d; font-size: 11px;")
        lbl_storage.setToolTip(str(storage_path))
        left_layout.addWidget(lbl_storage)

        main_layout.addWidget(left)

        # ─── Panel phải: Nội dung chi tiết (stacked: placeholder | system content) ───
        right = QFrame()
        right.setObjectName("monitoringRightPanel")
        right.setStyleSheet("""
            #monitoringRightPanel {
                background: #ffffff;
                border-left: 1px solid #d0d7de;
            }
        """)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.content_header = QLabel("Monitoring System")
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        self.content_header.setFont(font)
        self.content_header.setStyleSheet("color: #1b2a38; padding: 16px 24px 8px 24px;")
        right_layout.addWidget(self.content_header)

        self.stacked_right = QStackedWidget()
        self.placeholder_widget = QWidget()
        ph_layout = QVBoxLayout(self.placeholder_widget)
        ph_layout.setContentsMargins(24, 8, 24, 24)
        self.content_desc = QLabel(
            "Chọn hoặc tạo mới hệ thống cần giám sát từ panel bên trái. "
            "Dùng Save để lưu cấu hình, Delete để xóa hệ thống. "
            "Khi chọn hệ thống, bạn có thể thêm hàng/cột và ô đồ thị hoặc ô text đánh giá."
        )
        self.content_desc.setWordWrap(True)
        self.content_desc.setStyleSheet("color: #495057; line-height: 1.5;")
        ph_layout.addWidget(self.content_desc)
        ph_layout.addStretch(1)
        self.stacked_right.addWidget(self.placeholder_widget)

        self.system_content = SystemContentWidget(df_provider=self.df_provider, plot_provider=self.plot_provider)
        self.stacked_right.addWidget(self.system_content)
        right_layout.addWidget(self.stacked_right, 1)
        main_layout.addWidget(right, 1)

        # Load dữ liệu đã lưu
        self._load_from_storage()
        self._rebuild_list()

    def _load_from_storage(self) -> None:
        self.systems = load_all_systems()

    def _rebuild_list(self) -> None:
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, sys_cfg in enumerate(self.systems):
            btn = QPushButton(sys_cfg.name)
            btn.setProperty("system_id", sys_cfg.id)
            btn.setFixedHeight(40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 12px;
                    background: #f8f9fa;
                    color: #1b2a38;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #e9ecef;
                    border-color: #b6c7d8;
                }
                QPushButton:checked {
                    background: #cfe2f3;
                    color: #245cb6;
                    font-weight: bold;
                    border-color: #97b3d0;
                }
            """)
            btn.clicked.connect(lambda checked=False, cfg=sys_cfg: self._select_system(cfg))
            self.list_layout.insertWidget(self.list_layout.count() - 1, btn)

    def _select_system(self, cfg: SystemConfig) -> None:
        self._save_current_layout_to_system()
        self.current_system = cfg
        self.content_header.setText(cfg.name)
        layout_cfg = (cfg.config or {}).get("layout", {})
        self.system_content.set_layout_config(layout_cfg)
        self.stacked_right.setCurrentWidget(self.system_content)
        self.btn_delete.setEnabled(True)
        self._update_checked_state(cfg.id)

    def _save_current_layout_to_system(self) -> None:
        """Ghi layout hiện tại vào current_system trước khi đổi hệ thống."""
        if self.current_system is not None:
            if self.current_system.config is None:
                self.current_system.config = {}
            self.current_system.config["layout"] = self.system_content.get_layout_config()

    def _update_checked_state(self, selected_id: str) -> None:
        for i in range(self.list_layout.count() - 1):
            item = self.list_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if isinstance(w, QPushButton) and w.property("system_id") == selected_id:
                    w.setChecked(True)
                elif isinstance(w, QPushButton):
                    w.setChecked(False)

    def _on_add(self) -> None:
        name, ok = QInputDialog.getText(
            self, "Tạo hệ thống mới", "Tên hệ thống cần giám sát:"
        )
        if ok and name and name.strip():
            name = name.strip()
            cfg = SystemConfig(
                id=str(uuid.uuid4())[:8],
                name=name,
                created_at="",
                config={},
            )
            self.systems.append(cfg)
            self._rebuild_list()
            self._select_system(cfg)
            self._dirty = True
            self.btn_save.setEnabled(True)

    def _on_save(self) -> None:
        if not self.systems:
            return
        self._save_current_layout_to_system()
        if save_all_systems(self.systems):
            self._dirty = False
            self.btn_save.setEnabled(False)
            QMessageBox.information(
                self, "Đã lưu",
                f"Đã lưu {len(self.systems)} hệ thống vào Monitoring storage/"
            )
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể lưu cấu hình.")

    def _on_delete(self) -> None:
        if not self.current_system:
            return
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f'Bạn có chắc muốn xóa hệ thống "{self.current_system.name}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.systems = [s for s in self.systems if s.id != self.current_system.id]
            self.current_system = None
            self._rebuild_list()
            self.content_header.setText("Monitoring System")
            self.stacked_right.setCurrentWidget(self.placeholder_widget)
            self.btn_delete.setEnabled(False)
            self._dirty = True
            self.btn_save.setEnabled(True)
