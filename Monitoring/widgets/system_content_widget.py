"""
Widget nội dung hệ thống - layout theo hàng/cột (mỗi hàng có thể có số cột khác nhau).
Mỗi ô: right-click → Get Plot (lấy đồ thị hiện tại tab Plot) | Note (ghi text).
"""
from __future__ import annotations
import uuid
from typing import Optional, Callable
import pandas as pd
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QFrame,
    QPushButton,
    QLabel,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt
from Monitoring.widgets.placeholder_cell import PlaceholderCell
from Monitoring.plot_binding.plot_bound_cell import PlotBoundCell
from Monitoring.widgets.text_cell import TextCellWidget
from PySide6.QtWidgets import QFileDialog
from Monitoring.reporting.export_report_dialog import ExportReportDialog
from Monitoring.reporting.report_exporter import export_report_docx, export_report_pdf

def _default_layout() -> dict:
    # New format: row_cols allows each row to have different number of columns.
    # Example: {"row_cols": [1, 3, 2], "cells": [...]}
    return {"row_cols": [1], "cells": []}


def _get_cell_at(cells: list, row: int, col: int) -> dict | None:
    """Lấy cell config tại (row, col)."""
    for c in cells:
        if c.get("row") == row and c.get("col") == col:
            return c
    return None


class SystemContentWidget(QWidget):
    """
    Panel nội dung - layout theo hàng (mỗi hàng có thể có số cột khác nhau).
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
        self.active_row: int = 0

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Bố cục:"))

        self.btn_add_row = QPushButton("➕ Thêm hàng")
        self.btn_add_row.setStyleSheet("QPushButton { padding: 6px 12px; }")
        self.btn_add_row.clicked.connect(self._on_add_row)
        toolbar.addWidget(self.btn_add_row)

        self.btn_add_col = QPushButton("➕ Thêm cột (hàng đang chọn)")
        self.btn_add_col.setStyleSheet("QPushButton { padding: 6px 12px; }")
        self.btn_add_col.clicked.connect(self._on_add_col)
        toolbar.addWidget(self.btn_add_col)

        self.btn_remove_col = QPushButton("➖ Bớt cột (hàng đang chọn)")
        self.btn_remove_col.setStyleSheet("QPushButton { padding: 6px 12px; }")
        self.btn_remove_col.clicked.connect(self._on_remove_col)
        toolbar.addWidget(self.btn_remove_col)

        self.btn_remove_row = QPushButton("🗑️ Xóa hàng (hàng đang chọn)")
        self.btn_remove_row.setStyleSheet("QPushButton { padding: 6px 12px; }")
        self.btn_remove_row.clicked.connect(self._on_remove_row)
        toolbar.addWidget(self.btn_remove_row)

        toolbar.addWidget(QLabel("  |  "))
        # toolbar.addWidget(QLabel("Click ô bất kỳ để chọn hàng; Chuột phải → Get Plot / Note"))

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setStyleSheet("QPushButton { padding: 6px 12px; background: #e8f5e9; }")
        self.btn_refresh.setToolTip("Làm mới")
        self.btn_refresh.clicked.connect(self._on_refresh)
        toolbar.addWidget(self.btn_refresh)
        self.btn_export = QPushButton("📄 Export Report")
        self.btn_export.setStyleSheet("QPushButton { padding: 6px 12px; background: #e3f2fd; }")
        self.btn_export.setToolTip("Xuất báo cáo Word/PDF từ dashboard hiện tại")
        self.btn_export.clicked.connect(self._on_export_report)
        toolbar.addWidget(self.btn_export)
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # Scroll + rows container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumHeight(300)

        self.grid_container = QWidget()
        self.grid_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.rows_layout = QVBoxLayout(self.grid_container)
        self.rows_layout.setSpacing(12)
        self.rows_layout.setContentsMargins(8, 8, 8, 8)

        scroll.setWidget(self.grid_container)
        main_layout.addWidget(scroll, 1)

    def set_layout_config(self, config: dict) -> None:
        """Áp dụng config layout."""
        self.layout_config = config if config else _default_layout()

        # Backward compatibility: old format {rows, cols, cells}
        if "row_cols" not in self.layout_config:
            rows = max(1, int(self.layout_config.get("rows", 1)))
            cols = max(1, int(self.layout_config.get("cols", 1)))
            self.layout_config["row_cols"] = [cols for _ in range(rows)]

        if "cells" not in self.layout_config:
            self.layout_config["cells"] = []

        row_cols = self.layout_config.get("row_cols") or [1]
        row_cols = [max(1, int(x)) for x in row_cols]
        self.layout_config["row_cols"] = row_cols
        self.active_row = min(self.active_row, len(row_cols) - 1)

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
            "row_cols": self.layout_config.get("row_cols", [1]),
            "cells": cells,
        }

    def _clear_grid(self) -> None:
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.cell_widgets.clear()
        self.cell_pos.clear()

    def _rebuild_grid(self) -> None:
        self._clear_grid()

        row_cols = self.layout_config.get("row_cols") or [1]
        rows = max(1, len(row_cols))
        cells_cfg = self.layout_config.get("cells", [])

        max_cols = max(row_cols) if row_cols else 1

        for r in range(rows):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)

            cols_r = max(1, int(row_cols[r]))
            for c in range(cols_r):
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
                    row_layout.addWidget(w, 1)
                else:
                    ph = PlaceholderCell(r, c)
                    ph.get_plot_requested.connect(self._on_get_plot)
                    ph.note_requested.connect(self._on_note)
                    ph.selected.connect(self._on_cell_selected)
                    row_layout.addWidget(ph, 1)

            self.rows_layout.addWidget(row_widget)

        min_w = max(400, max_cols * 320)
        min_h = max(300, rows * 220)
        self.grid_container.setMinimumSize(min_w, min_h)

    def _on_cell_selected(self, row: int, col: int) -> None:
        self.active_row = max(0, row)

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
        self.active_row = row

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
        self.active_row = row

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
        row_cols = self.layout_config.get("row_cols") or [1]
        inherit_cols = row_cols[self.active_row] if 0 <= self.active_row < len(row_cols) else row_cols[-1]
        row_cols.append(max(1, int(inherit_cols)))
        self.layout_config["row_cols"] = row_cols
        self.active_row = len(row_cols) - 1
        self._rebuild_grid()

    def _on_add_col(self) -> None:
        row_cols = self.layout_config.get("row_cols") or [1]
        if not row_cols:
            row_cols = [1]
        r = min(max(0, self.active_row), len(row_cols) - 1)
        row_cols[r] = max(1, int(row_cols[r])) + 1
        self.layout_config["row_cols"] = row_cols
        self.active_row = r
        self._rebuild_grid()

    def _on_remove_col(self) -> None:
        row_cols = self.layout_config.get("row_cols") or [1]
        if not row_cols:
            return
        r = min(max(0, self.active_row), len(row_cols) - 1)
        if row_cols[r] <= 1:
            return

        new_cols = row_cols[r] - 1
        cells = self.layout_config.get("cells", [])
        self.layout_config["cells"] = [
            c for c in cells
            if not (c.get("row") == r and int(c.get("col", 0)) >= new_cols)
        ]
        row_cols[r] = new_cols
        self.layout_config["row_cols"] = row_cols
        self.active_row = r
        self._rebuild_grid()

    def _on_remove_row(self) -> None:
        row_cols = self.layout_config.get("row_cols") or [1]
        if len(row_cols) <= 1:
            return
        r = min(max(0, self.active_row), len(row_cols) - 1)

        new_cells = []
        for c in self.layout_config.get("cells", []):
            rr = int(c.get("row", 0))
            if rr == r:
                continue
            if rr > r:
                c = dict(c)
                c["row"] = rr - 1
            new_cells.append(c)
        self.layout_config["cells"] = new_cells

        row_cols.pop(r)
        self.layout_config["row_cols"] = row_cols
        self.active_row = min(r, len(row_cols) - 1)
        self._rebuild_grid()

    def _on_refresh(self) -> None:
        self._rebuild_grid()
    def _on_export_report(self) -> None:
        dlg = ExportReportDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        title, fmt = dlg.get_values()  # fmt: "docx" or "pdf"
        if not title.strip():
            title = "Monitoring Report"

        default_name = f"{title.strip().replace('/', '-').replace('\\', '-')}.{fmt}"

        if fmt == "docx":
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Report (Word)", default_name, "Word Document (*.docx)"
            )
            if not save_path:
                return
            if not save_path.lower().endswith(".docx"):
                save_path += ".docx"
            export_report_docx(save_path, title, self)
        else:
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Report (PDF)", default_name, "PDF File (*.pdf)"
            )
            if not save_path:
                return
            if not save_path.lower().endswith(".pdf"):
                save_path += ".pdf"
            export_report_pdf(save_path, title, self)

        QMessageBox.information(self, "Export Report", f"Đã xuất báo cáo:\n{save_path}")