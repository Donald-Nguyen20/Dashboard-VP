"""
Widget nội dung hệ thống - layout theo hàng/cột (mỗi hàng có thể có số cột khác nhau).
Mỗi ô: right-click → Get Plot (lấy nguyên đồ thị từ tab Plotly, cùng cách thức như Plot: nội dung tab → nhúng trực tiếp) | Note (ghi text).
"""
from __future__ import annotations
import base64
import uuid
from io import BytesIO
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
from PySide6.QtCore import Qt, Signal
from Monitoring.widgets.placeholder_cell import PlaceholderCell
from Monitoring.plot_binding.plot_bound_cell import PlotBoundCell
from Monitoring.widgets.text_cell import TextCellWidget
from Monitoring.widgets.plot_image_cell import PlotImageCell
from Monitoring.widgets.plotly_embed_cell import PlotlyEmbedCell
from PySide6.QtWidgets import QFileDialog
from Monitoring.reporting.export_report_dialog import ExportReportDialog
from Monitoring.reporting.report_exporter import export_report_docx, export_report_pdf, PdfLayoutConfig
from Monitoring.widgets.operating_report_panel import OperatingReportPanel
from reportlab.lib.units import mm
import os, tempfile
from PySide6.QtGui import QPixmap
from reportlab.lib.pagesizes import A4, landscape
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import QPoint
from Monitoring.widgets.plotly_spec_cell import PlotlySpecCell
from PySide6.QtWidgets import QDateTimeEdit
from PySide6.QtCore import QDateTime
def save_widget_high_res(widget, path, scale_factor=3):
    w = max(1, widget.width())
    h = max(1, widget.height())

    img = QImage(w * scale_factor, h * scale_factor, QImage.Format_ARGB32)
    img.fill(Qt.white)

    painter = QPainter(img)
    painter.scale(scale_factor, scale_factor)

    # ✅ PySide6 yêu cầu targetOffset khi render với QPainter
    widget.render(painter, QPoint(0, 0))

    painter.end()
    img.save(path)
def normalize_row_image(img_path: str, target_w_px: int = 2400, min_h_px: int = 1400):
    """Ép ảnh về width chuẩn, và đảm bảo height không bị lùn (ổn định mọi máy)."""
    try:
        from PIL import Image as PILImage
    except Exception:
        return

    try:
        im = PILImage.open(img_path)
        w, h = im.size
        if w <= 0 or h <= 0:
            return

        # scale theo width chuẩn
        scale = target_w_px / float(w)
        new_w = target_w_px
        new_h = int(h * scale)

        # đảm bảo không lùn hơn mức tối thiểu
        if new_h < min_h_px:
            new_h = min_h_px

        im = im.resize((new_w, new_h), PILImage.LANCZOS)
        im.save(img_path)
    except Exception:
        pass
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
    layout_changed = Signal()
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
        # ===== Time range (global) =====
        rangebar = QHBoxLayout()
        rangebar.addWidget(QLabel("⏱ From:"))

        self.dt_start = QDateTimeEdit(QDateTime.currentDateTime().addSecs(-15552000))  # mặc định 180 ngày trước
        self.dt_start.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.dt_start.setCalendarPopup(True)
        rangebar.addWidget(self.dt_start)

        rangebar.addWidget(QLabel("To:"))
        self.dt_end = QDateTimeEdit(QDateTime.currentDateTime())
        self.dt_end.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.dt_end.setCalendarPopup(True)
        rangebar.addWidget(self.dt_end)

        self.btn_apply_range = QPushButton("Apply")
        self.btn_apply_range.clicked.connect(self._on_apply_time_range)
        rangebar.addStretch()
        rangebar.addWidget(self.btn_apply_range)

        main_layout.addLayout(rangebar)
        # Scroll + rows container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumHeight(300)

        self.grid_container = QWidget()
        self.grid_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.scroll_root_layout = QVBoxLayout(self.grid_container)
        self.scroll_root_layout.setSpacing(12)
        self.scroll_root_layout.setContentsMargins(8, 8, 8, 8)

        # layout chứa rows (phần này sẽ bị clear/rebuild)
        self.rows_holder = QWidget(self.grid_container)
        self.rows_layout = QVBoxLayout(self.rows_holder)
        self.rows_layout.setSpacing(12)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)

        # add rows holder vào root layout
        self.scroll_root_layout.addWidget(self.rows_holder)

        # report panel đặt dưới cùng và KHÔNG bị clear
        self.report_panel = OperatingReportPanel(self.grid_container)
        self.scroll_root_layout.addWidget(self.report_panel)

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
    def _mark_dirty(self) -> None:
        self.layout_changed.emit()
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
            elif isinstance(w, PlotImageCell):
                cells.append({
                    "cell_id": cell_id,
                    "row": r,
                    "col": c,
                    "type": "plot_image",
                    "image_base64": getattr(w, "image_base64", "") or "",
                })
            elif isinstance(w, PlotlyEmbedCell):
                cells.append({
                    "cell_id": cell_id,
                    "row": r,
                    "col": c,
                    "type": "plotly_embed",
                    "html_content": getattr(w, "html_content", "") or "",
                })
            elif isinstance(w, TextCellWidget):
                cells.append({
                    "cell_id": cell_id,
                    "row": r,
                    "col": c,
                    "type": "note",
                    "text_content": w.get_content(),
                })
            elif isinstance(w, PlotlySpecCell):
                cells.append({
                    "cell_id": cell_id,
                    "row": r,
                    "col": c,
                    "type": "plotly_spec",
                    "plotly_spec": getattr(w, "spec", {}) or {},
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

        ROW_H = 900  # 280/320/360 tùy thích

        for r in range(rows):
            row_widget = QWidget()
            row_widget.setMinimumHeight(ROW_H)
            row_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

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
                        w = PlotBoundCell(plot_spec=cell_info.get("plot_spec", {}), df_provider=self.df_provider)
                        w.on_clear = lambda row=r, col=c: self._on_clear_cell(row, col)
                        w.on_refresh = lambda row=r, col=c: self._on_refresh_plot_cell(row, col)

                    elif ctype == "plot_image":
                        w = PlotImageCell(image_base64=cell_info.get("image_base64", ""))
                        w.on_clear = lambda row=r, col=c: self._on_clear_cell(row, col)
                        w.on_refresh = lambda row=r, col=c: self._on_refresh_plot_image_cell(row, col)

                    elif ctype == "plotly_spec":
                        w = PlotlySpecCell(
                            spec=cell_info.get("plotly_spec", {}) or {},
                            df_provider=self.df_provider,
                            time_provider=lambda: (
                                self.dt_start.dateTime().toPython(),
                                self.dt_end.dateTime().toPython()
                            ),
                        )

                        # refresh cell = rerender
                        w.on_refresh = lambda row=r, col=c: self._on_apply_time_range()
                        w.on_clear = lambda row=r, col=c: self._on_clear_cell(row, col)

                    else:
                        w = TextCellWidget(initial_text=cell_info.get("text_content", ""))
                        w.on_clear = lambda row=r, col=c: self._on_clear_cell(row, col)

                    self.cell_widgets[cell_id] = w
                    self.cell_pos[cell_id] = (r, c)

                    w.setMinimumHeight(ROW_H)
                    w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    row_layout.addWidget(w, 1)

                else:
                    ph = PlaceholderCell(r, c)
                    ph.get_plot_requested.connect(self._on_get_plot)
                    ph.note_requested.connect(self._on_note)
                    ph.selected.connect(self._on_cell_selected)

                    ph.setMinimumHeight(ROW_H)
                    ph.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    row_layout.addWidget(ph, 1)

            self.rows_layout.addWidget(row_widget)

        min_w = max(400, max_cols * 320)
        # spacing=12, margins top+bottom = 8+8 = 16
        min_h = max(300, rows * ROW_H + (rows - 1) * 12 + 16)
        self.grid_container.setMinimumSize(min_w, min_h)

    def _on_cell_selected(self, row: int, col: int) -> None:
        self.active_row = max(0, row)

    def _get_plot_spec(self) -> dict | None:
        """Lấy PlotSpec từ tab Plot (cho ô plot_bound cũ)."""
        plot_tab = self.plot_provider() if self.plot_provider else None
        if plot_tab is None:
            return None
        getter = getattr(plot_tab, "get_current_plot_spec", None)
        if not callable(getter):
            return None
        return getter()

    def _get_plotly_html_content(self) -> tuple[str | None, str | None]:
        """Lấy nguyên nội dung HTML đồ thị từ tab Plotly (cùng cách thức Plot: nội dung tab → nhúng). Không dùng kaleido/subprocess."""
        plotly_tab = self.plot_provider() if self.plot_provider else None
        if plotly_tab is None:
            return None, "Không tìm thấy tab Plotly."
        getter = getattr(plotly_tab, "get_last_html_content", None)
        if not callable(getter):
            return None, "Tab Plotly không hỗ trợ lấy đồ thị."
        html_content = getter()
        if html_content:
            return html_content, None
        return None, "Chưa có đồ thị. Vẽ đồ thị tại tab Plotly (Data Analyzing) trước, sau đó chuột phải → Get Plot."

    def _capture_matplotlib_as_base64(self) -> str | None:
        """Chụp figure từ tab Plot (matplotlib) ra PNG base64 - cho ô ảnh cũ."""
        plot_tab = self.plot_provider() if self.plot_provider else None
        if plot_tab is None:
            return None
        fig = getattr(plot_tab, "figure", None)
        if fig is None:
            return None
        buf = BytesIO()
        try:
            fig.savefig(buf, format="png")
            buf.seek(0)
            return base64.b64encode(buf.read()).decode("ascii")
        except Exception:
            return None

    def _on_get_plot(self, row: int, col: int) -> None:
        self.active_row = row

        plotly_tab = self.plot_provider() if self.plot_provider else None
        if plotly_tab is None:
            QMessageBox.warning(self, "Chưa có đồ thị", "Không tìm thấy tab Plotly.")
            return

        spec_getter = getattr(plotly_tab, "get_current_plotly_spec", None)
        if not callable(spec_getter):
            QMessageBox.warning(self, "Thiếu hỗ trợ", "PlotlyTab chưa có get_current_plotly_spec().")
            return

        spec = spec_getter()
        if not spec or not spec.get("selected_vars"):
            QMessageBox.warning(self, "Chưa chọn biến", "Vào tab Plotly chọn biến + loại chart trước.")
            return

        cell_id = str(uuid.uuid4())[:8]
        self.layout_config["cells"].append({
            "cell_id": cell_id,
            "row": row,
            "col": col,
            "type": "plotly_spec",
            "plotly_spec": spec,
        })
        self._rebuild_grid()
        self._mark_dirty()

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
        self._mark_dirty()

    def _on_clear_cell(self, row: int, col: int) -> None:
        """Xóa nội dung ô → trở về placeholder."""
        cells = self.layout_config.get("cells", [])
        self.layout_config["cells"] = [c for c in cells if not (c.get("row") == row and c.get("col") == col)]
        self._rebuild_grid()
        self._mark_dirty()

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
        self._mark_dirty()

    def _on_refresh_plot_image_cell(self, row: int, col: int) -> None:
        """Chụp lại đồ thị từ tab Plot (matplotlib) cho ô ảnh (row, col)."""
        b64 = self._capture_matplotlib_as_base64()
        if not b64:
            QMessageBox.warning(self, "Chưa có đồ thị", "Vẽ đồ thị tại tab Plot trước.")
            return
        cells = self.layout_config.get("cells", [])
        for c in cells:
            if c.get("row") == row and c.get("col") == col and c.get("type") == "plot_image":
                c["image_base64"] = b64
                break
        self._rebuild_grid()
        self._mark_dirty()

    def _on_refresh_plotly_embed_cell(self, row: int, col: int) -> None:
        """Lấy lại nguyên đồ thị từ tab Plotly cho ô plotly_embed (row, col)."""
        html_content, err_msg = self._get_plotly_html_content()
        if not html_content:
            QMessageBox.warning(self, "Chưa có đồ thị", err_msg or "Vẽ đồ thị tại tab Plotly trước.")
            return
        cells = self.layout_config.get("cells", [])
        for c in cells:
            if c.get("row") == row and c.get("col") == col and c.get("type") == "plotly_embed":
                c["html_content"] = html_content
                break
        self._rebuild_grid()
        self._mark_dirty()

    def _on_add_row(self) -> None:
        row_cols = self.layout_config.get("row_cols") or [1]
        inherit_cols = row_cols[self.active_row] if 0 <= self.active_row < len(row_cols) else row_cols[-1]
        row_cols.append(max(1, int(inherit_cols)))
        self.layout_config["row_cols"] = row_cols
        self.active_row = len(row_cols) - 1
        self._rebuild_grid()
        self._mark_dirty()

    def _on_add_col(self) -> None:
        row_cols = self.layout_config.get("row_cols") or [1]
        if not row_cols:
            row_cols = [1]
        r = min(max(0, self.active_row), len(row_cols) - 1)
        row_cols[r] = max(1, int(row_cols[r])) + 1
        self.layout_config["row_cols"] = row_cols
        self.active_row = r
        self._rebuild_grid()
        self._mark_dirty()
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
        self._mark_dirty()



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
        self._mark_dirty()
    def _on_refresh(self) -> None:
        self._rebuild_grid()
        self._mark_dirty()
    def _on_export_report(self) -> None:
        dlg = ExportReportDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        title, fmt = dlg.get_values()  # fmt: "docx" or "pdf"
        if not title.strip():
            title = "Monitoring Report"

        default_name = f"{title.strip().replace('/', '-').replace('\\', '-')}.{fmt}"

        # 1) hỏi nơi lưu trước
        if fmt == "docx":
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Report (Word)", default_name, "Word Document (*.docx)"
            )
            if not save_path:
                return
            if not save_path.lower().endswith(".docx"):
                save_path += ".docx"
        else:
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Report (PDF)", default_name, "PDF File (*.pdf)"
            )
            if not save_path:
                return
            if not save_path.lower().endswith(".pdf"):
                save_path += ".pdf"

        # 2) Temp folder (dùng chung cho cả PDF & DOCX)
        temp_dir = os.path.join(tempfile.gettempdir(), "dashboard_reports")
        os.makedirs(temp_dir, exist_ok=True)
        for fn in os.listdir(temp_dir):
            if fn.lower().startswith("cell_") and fn.lower().endswith(".png"):
                try:
                    os.remove(os.path.join(temp_dir, fn))
                except Exception:
                    pass

        # 3) Chụp từng ROW dashboard → mỗi row = 1 ảnh
        image_paths = []

        for i in range(self.rows_layout.count()):
            row_widget = self.rows_layout.itemAt(i).widget()
            if row_widget is None:
                continue

            img_path = os.path.join(temp_dir, f"cell_row_{i+1}.png")
            save_widget_high_res(row_widget, img_path, scale_factor=3)

            # ✅ CHÌA KHOÁ: chuẩn hoá ảnh để mọi máy ra như nhau + cao hơn
            normalize_row_image(img_path, target_w_px=2400, min_h_px=1000)

            image_paths.append(img_path)

        # 4) Config đồng bộ giữa PDF & DOCX (A4 ngang như anh đang dùng)
        cfg = PdfLayoutConfig(
            pagesize=landscape(A4),
            split_tall_images=True,
            title_on_first_page_only=False,
            always_full_width=True,
            margin_left=5*mm,
            margin_right=5*mm,
            margin_top=5*mm,
            margin_bottom=5*mm
        )

        # 5) Export theo định dạng
        if fmt == "pdf":
            export_report_pdf(
                save_path,
                title,
                self,
                temp_image_dir=temp_dir,
                image_paths=image_paths,
                cfg=cfg
            )
        else:
            # ✅ Quan trọng: truyền temp_image_dir + cfg (và ảnh đã chụp)
            # Nếu exporter của anh hỗ trợ image_paths thì truyền thêm image_paths=[img_path].
            # Nếu exporter tự collect cell_*.png thì chỉ cần temp_image_dir.
            export_report_docx(
                save_path,
                title,
                self,
                temp_image_dir=temp_dir,
                image_paths=image_paths,
                cfg=cfg
            )

        QMessageBox.information(self, "Export Report", f"Đã xuất báo cáo:\n{save_path}")
    def _on_apply_time_range(self) -> None:
        # 1) rerender tất cả cell plotly_spec
        for w in self.cell_widgets.values():
            if isinstance(w, PlotlySpecCell):
                w.rerender()

        # 2) lấy df gốc
        df = self.df_provider() if self.df_provider else None
        if df is None or df.empty:
            if hasattr(self, "report_panel") and self.report_panel:
                self.report_panel.clear()
            return

        # 3) detect time column
        time_col = None
        for cand in ("Datetime", "datetime", "DATE_TIME", "Time", "time", "timestamp", "Timestamp"):
            if cand in df.columns:
                time_col = cand
                break

        # 4) filter df_range theo time range (dt_start/dt_end)
        if time_col is None:
            # fallback: assume index is time (không filter được chắc chắn)
            df_range = df.copy()
        else:
            d = df.copy()
            d[time_col] = pd.to_datetime(d[time_col], errors="coerce")
            d = d.dropna(subset=[time_col]).sort_values(time_col)

            start = self.dt_start.dateTime().toPython()
            end = self.dt_end.dateTime().toPython()
            df_range = d[(d[time_col] >= start) & (d[time_col] <= end)]

        if df_range is None or df_range.empty:
            if hasattr(self, "report_panel") and self.report_panel:
                self.report_panel.clear()
            return

        # 5) chọn MW column (nếu có)
        mw_col = None
        for cand in ("NET MW", "MW", "NetMW", "Unit Load", "Load"):
            if cand in df_range.columns:
                mw_col = cand
                break

        # 6) chọn danh sách tags để đưa vào báo cáo:
        #    - ưu tiên: các cột numeric
        #    - bỏ qua time_col và MW
        ignore = set()
        if time_col:
            ignore.add(time_col)
        if mw_col:
            ignore.add(mw_col)

        tags = []
        for c in df_range.columns:
            if c in ignore:
                continue
            s = pd.to_numeric(df_range[c], errors="coerce")
            if s.notna().sum() >= 20:  # report nên yêu cầu nhiều điểm hơn chút
                tags.append(c)

        # 7) update report panel (narrative)
        if hasattr(self, "report_panel") and self.report_panel:
            self.report_panel.update_report(
                df_range=df_range,
                tags=tags,
                time_col=time_col,
                mw_col=mw_col,
            )