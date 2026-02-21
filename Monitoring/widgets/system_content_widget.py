"""
Widget nội dung hệ thống - layout theo hàng/cột.
Mỗi ô: right-click → Get Plot (lấy đồ thị hiện tại tab Plot) | Note (ghi text).
"""
from __future__ import annotations
import base64
import io
import uuid
from typing import Optional, Callable
import pandas as pd
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QScrollArea,
    QFrame,
    QPushButton,
    QLabel,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from Monitoring.widgets.placeholder_cell import PlaceholderCell
from Monitoring.plot_binding.plot_bound_cell import PlotBoundCell
from Monitoring.widgets.text_cell import TextCellWidget


def _default_layout() -> dict:
    return {"rows": 1, "cols": 1, "cells": []}


def _get_cell_at(cells: list, row: int, col: int) -> dict | None:
    """Lấy cell config tại (row, col)."""
    for c in cells:
        if c.get("row") == row and c.get("col") == col:
            return c
    return None


class SystemContentWidget(QWidget):
    """
    Panel nội dung - grid hiển thị rõ hàng/cột.
    Mỗi ô: right-click → Get Plot | Note.
    """
    def __init__(
        self,
        df_provider: Callable[[], pd.DataFrame | None] | None = None,
        plot_provider: Callable[[], object] | None = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.df_provider = df_provider or (lambda: None)
        self.plot_provider = plot_provider or (lambda: None)
        self.layout_config = _default_layout()
        self.cell_widgets: dict[str, QWidget] = {}
        self.cell_pos: dict[str, tuple[int, int]] = {}  # cell_id -> (row, col)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar: chỉ Thêm hàng / Thêm cột
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Bố cục:"))
        self.btn_add_row = QPushButton("➕ Thêm hàng")
        self.btn_add_row.setStyleSheet("QPushButton { padding: 6px 12px; }")
        self.btn_add_row.clicked.connect(self._on_add_row)
        toolbar.addWidget(self.btn_add_row)

        self.btn_add_col = QPushButton("➕ Thêm cột")
        self.btn_add_col.setStyleSheet("QPushButton { padding: 6px 12px; }")
        self.btn_add_col.clicked.connect(self._on_add_col)
        toolbar.addWidget(self.btn_add_col)

        toolbar.addWidget(QLabel("  |  "))
        toolbar.addWidget(QLabel("Chuột phải vào ô trống → Get Plot / Note"))

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setStyleSheet("QPushButton { padding: 6px 12px; background: #e8f5e9; }")
        self.btn_refresh.setToolTip("Làm mới")
        self.btn_refresh.clicked.connect(self._on_refresh)
        toolbar.addWidget(self.btn_refresh)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # Scroll + grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumHeight(300)
        self.grid_container = QWidget()
        self.grid_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        scroll.setWidget(self.grid_container)
        main_layout.addWidget(scroll, 1)

    def set_layout_config(self, config: dict) -> None:
        """Áp dụng config layout."""
        self.layout_config = config if config else _default_layout()
        if "rows" not in self.layout_config:
            self.layout_config["rows"] = 1
        if "cols" not in self.layout_config:
            self.layout_config["cols"] = 1
        if "cells" not in self.layout_config:
            self.layout_config["cells"] = []
        self._rebuild_grid()

    def get_layout_config(self) -> dict:
        """Lấy config hiện tại."""
        cells = []
        for cell_id, pos in self.cell_pos.items():
            r, c = pos
            w = self.cell_widgets.get(cell_id)
            if isinstance(w, PlotBoundCell):
                cells.append({
                    "cell_id": cell_id,
                    "row": r,
                    "col": c,
                    "type": "plot_bound",
                    "plot_spec": w.plot_spec,
                })
            elif isinstance(w, TextCellWidget):
                cells.append({
                    "cell_id": cell_id,
                    "row": r,
                    "col": c,
                    "type": "note",
                    "text_content": w.get_content(),
                })
        return {
            "rows": self.layout_config["rows"],
            "cols": self.layout_config["cols"],
            "cells": cells,
        }

    def _clear_grid(self) -> None:
        for cell_id, w in list(self.cell_widgets.items()):
            self.grid_layout.removeWidget(w)
            w.deleteLater()
        self.cell_widgets.clear()
        self.cell_pos.clear()

    def _rebuild_grid(self) -> None:
        self._clear_grid()
        rows = max(1, self.layout_config.get("rows", 1))
        cols = max(1, self.layout_config.get("cols", 1))
        cells_cfg = self.layout_config.get("cells", [])

        for r in range(rows):
            for c in range(cols):
                cell_info = _get_cell_at(cells_cfg, r, c)
                if cell_info:
                    cell_id = cell_info.get("cell_id") or str(uuid.uuid4())[:8]
                    ctype = cell_info.get("type", "note")
                    if ctype == "plot_bound":
                        w = PlotBoundCell(
                            plot_spec=cell_info.get("plot_spec", {}),
                            df_provider=self.df_provider
                        )
                        w.on_clear = lambda row=r, col=c: self._on_clear_cell(row, col)
                        w.on_refresh = lambda row=r, col=c: self._on_refresh_plot_cell(row, col)
                    else:
                        w = TextCellWidget(initial_text=cell_info.get("text_content", ""))
                        w.on_clear = lambda row=r, col=c: self._on_clear_cell(row, col)
                    self.cell_widgets[cell_id] = w
                    self.cell_pos[cell_id] = (r, c)
                    self.grid_layout.addWidget(w, r, c)
                else:
                    ph = PlaceholderCell(r, c)
                    ph.get_plot_requested.connect(self._on_get_plot)
                    ph.note_requested.connect(self._on_note)
                    self.grid_layout.addWidget(ph, r, c)

        min_w = max(400, cols * 320)
        min_h = max(300, rows * 220)
        self.grid_container.setMinimumSize(min_w, min_h)

    def _get_plot_spec(self) -> dict | None:
        """Lấy PlotSpec hiện tại từ tab Plot (Data Analyzing)."""
        plot_tab = self.plot_provider() if self.plot_provider else None
        if plot_tab is None:
            return None
        getter = getattr(plot_tab, "get_current_plot_spec", None)
        if not callable(getter):
            return None
        return getter()

    def _on_get_plot(self, row: int, col: int) -> None:
        """Bind đồ thị hiện tại từ tab Plot vào ô (row, col) bằng PlotSpec (không ảnh)."""
        spec = self._get_plot_spec()
        if spec is None:
            QMessageBox.warning(
                self,
                "Chưa có đồ thị",
                "Vẽ đồ thị tại tab Plot (Data Analyzing) trước, sau đó chuột phải → Get Plot."
            )
            return

        cell_id = str(uuid.uuid4())[:8]
        self.layout_config["cells"].append({
            "cell_id": cell_id,
            "row": row,
            "col": col,
            "type": "plot_bound",
            "plot_spec": spec,
        })
        self._rebuild_grid()

    def _on_note(self, row: int, col: int) -> None:
        """Thêm ô Note tại (row, col)."""
        cell_id = str(uuid.uuid4())[:8]
        self.layout_config["cells"].append({
            "cell_id": cell_id,
            "row": row,
            "col": col,
            "type": "note",
            "text_content": "",
        })
        self._rebuild_grid()

    def _on_clear_cell(self, row: int, col: int) -> None:
        """Xóa nội dung ô → trở về placeholder."""
        cells = self.layout_config.get("cells", [])
        self.layout_config["cells"] = [c for c in cells if not (c.get("row") == row and c.get("col") == col)]
        self._rebuild_grid()

    def _on_refresh_plot_cell(self, row: int, col: int) -> None:
        """Re-bind PlotSpec mới nhất từ tab Plot cho ô (row, col)."""
        spec = self._get_plot_spec()
        if spec is None:
            QMessageBox.warning(self, "Chưa có đồ thị", "Vẽ đồ thị tại tab Plot trước.")
            return

        cells = self.layout_config.get("cells", [])
        for c in cells:
            if c.get("row") == row and c.get("col") == col and c.get("type") == "plot_bound":
                c["plot_spec"] = spec
                break
        self._rebuild_grid()

    def _on_add_row(self) -> None:
        self.layout_config["rows"] = self.layout_config.get("rows", 1) + 1
        self._rebuild_grid()

    def _on_add_col(self) -> None:
        self.layout_config["cols"] = self.layout_config.get("cols", 1) + 1
        self._rebuild_grid()

    def _on_refresh(self) -> None:
        self._rebuild_grid()
