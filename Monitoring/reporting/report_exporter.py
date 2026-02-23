from __future__ import annotations
import base64
import os
import time
import datetime as dt
from typing import List, Optional

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

# Word
from docx import Document
from docx.shared import Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

# Chất lượng xuất: DPI cao cho matplotlib, scale 2x cho đồ thị web (Plotly)
EXPORT_FIGURE_DPI = 300
EXPORT_WEBVIEW_SCALE = 2
# PDF: chiều cao tối đa ảnh trên 1 trang (point) — tránh LayoutError "too large on page"
PDF_MAX_IMAGE_HEIGHT = 620


def _safe_temp_dir() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
    out = os.path.join(base, "dashboard_reports")
    os.makedirs(out, exist_ok=True)
    return out


def _grab_widget_png(widget, out_path: str) -> bool:
    if widget is None:
        return False

    # 1) Matplotlib (PlotBoundCell): xuất trực tiếp từ figure, DPI cao → nét nhất
    if _save_plotboundcell_figure(widget, out_path, dpi=EXPORT_FIGURE_DPI):
        return True

    # 2) PlotImageCell: dùng ảnh gốc (base64), không grab → giữ nguyên chất lượng
    if _save_plotimagecell_raw(widget, out_path):
        return True

    # 3) PlotlyEmbedCell: chụp web_view ở độ phân giải 2x → ảnh đẹp hơn
    if _grab_plotlyembed_high_res(widget, out_path, scale=EXPORT_WEBVIEW_SCALE):
        return True

    # 4) Fallback: chụp widget bình thường
    try:
        pix: QPixmap = widget.grab()
        if pix.isNull():
            return False
        return pix.save(out_path, "PNG")
    except Exception:
        return False


def _save_plotboundcell_figure(widget, out_path: str, dpi: int = 300) -> bool:
    """
    Xuất trực tiếp từ matplotlib Figure (PlotBoundCell) — vector-quality, DPI cao.
    """
    fig = getattr(widget, "figure", None)
    if fig is None:
        return False
    savefig = getattr(fig, "savefig", None)
    if not callable(savefig):
        return False
    try:
        fig.savefig(
            out_path,
            dpi=dpi,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        return True
    except Exception:
        return False


def _save_plotimagecell_raw(widget, out_path: str) -> bool:
    """
    Ô ảnh (PlotImageCell): ghi thẳng ảnh gốc từ image_base64 — không qua grab, chất lượng tốt nhất.
    """
    b64 = getattr(widget, "image_base64", None)
    if not b64 or not isinstance(b64, str):
        return False
    try:
        raw = base64.b64decode(b64)
        if raw:
            with open(out_path, "wb") as f:
                f.write(raw)
            return True
    except Exception:
        pass
    return False


def _grab_plotlyembed_high_res(widget, out_path: str, scale: int = 2) -> bool:
    """
    PlotlyEmbedCell: tạm phóng to web_view rồi grab → ảnh độ phân giải cao hơn.
    """
    web_view = getattr(widget, "web_view", None)
    if web_view is None:
        return False
    try:
        old_w = web_view.width()
        old_h = web_view.height()
        if old_w <= 0 or old_h <= 0:
            return False
        new_w = old_w * scale
        new_h = old_h * scale
        web_view.setFixedSize(new_w, new_h)
        for _ in range(4):
            QApplication.processEvents()
        time.sleep(0.15)
        QApplication.processEvents()
        pix = web_view.grab()
        web_view.setFixedSize(old_w, old_h)
        if pix.isNull():
            web_view.setMinimumSize(260, 180)
            return False
        ok = pix.save(out_path, "PNG")
        web_view.setMinimumSize(260, 180)
        return ok
    except Exception:
        try:
            web_view.setMinimumSize(260, 180)
        except Exception:
            pass
        return False

def _pdf_image_fit_page(img_path: str, col_w: float, max_height: float = PDF_MAX_IMAGE_HEIGHT):
    """Tạo RLImage vừa khung trang: bề ngang col_w, chiều cao tối đa max_height, giữ tỷ lệ."""
    try:
        ir = ImageReader(img_path)
        pw, ph = ir.getSize()
        if pw <= 0 or ph <= 0:
            return RLImage(img_path, width=col_w)
        # Tính kích thước hiển thị (point) giữ tỷ lệ, không vượt col_w và max_height
        aspect = ph / pw
        if col_w * aspect <= max_height:
            return RLImage(img_path, width=col_w)
        return RLImage(img_path, height=max_height)
    except Exception:
        return RLImage(img_path, width=col_w)


def _build_widget_matrix(system_widget) -> List[List[Optional[object]]]:
    """
    Trả về ma trận widget theo đúng bố cục dashboard:
    - số hàng = len(row_cols)
    - số cột = max(row_cols)
    - ô không tồn tại ở hàng ngắn hơn => None
    """
    row_cols = system_widget.layout_config.get("row_cols", [1])
    row_cols = [max(1, int(x)) for x in row_cols]
    max_cols = max(row_cols) if row_cols else 1

    # map (r,c) -> widget
    by_pos = {}
    for cid, (r, c) in system_widget.cell_pos.items():
        by_pos[(r, c)] = system_widget.cell_widgets.get(cid)

    matrix: List[List[Optional[object]]] = []
    for r, cols_r in enumerate(row_cols):
        row = []
        for c in range(max_cols):
            if c < cols_r:
                row.append(by_pos.get((r, c)))
            else:
                row.append(None)  # hàng này không có cột đó
        matrix.append(row)
    return matrix


def _docx_remove_table_borders(table) -> None:
    """Bỏ toàn bộ viền bảng Word."""
    for row in table.rows:
        for cell in row.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcBorders = OxmlElement("w:tcBorders")
            for side in ("top", "left", "bottom", "right"):
                el = OxmlElement(f"w:{side}")
                el.set(qn("w:val"), "nil")
                tcBorders.append(el)
            tcPr.append(tcBorders)


def export_report_docx(save_path: str, title: str, system_widget) -> None:
    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(f"Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph("")

    temp_dir = _safe_temp_dir()
    matrix = _build_widget_matrix(system_widget)

    rows = len(matrix)
    cols = len(matrix[0]) if rows else 1

    # Lắp đầy trang: dùng hết bề ngang (trừ margin ~1" mỗi bên → ~6.5")
    usable_width_in = 6.5
    img_width_in = usable_width_in / max(cols, 1)

    table = doc.add_table(rows=rows, cols=cols)
    table.style = "Table Grid"
    table.autofit = False
    col_width = Inches(usable_width_in / max(cols, 1))
    for col in table.columns:
        for cell in col.cells:
            cell.width = col_width

    _docx_remove_table_borders(table)

    for r in range(rows):
        for c in range(cols):
            cell = table.cell(r, c)
            w = matrix[r][c]

            if w is None:
                cell.text = ""
                continue

            get_content = getattr(w, "get_content", None)
            if callable(get_content):
                text = (get_content() or "").strip()
                cell.text = text if text else ""
                continue

            img_path = os.path.join(temp_dir, f"cell_r{r+1}_c{c+1}.png")
            ok = _grab_widget_png(w, img_path)
            if ok and os.path.exists(img_path):
                cell.text = ""
                p = cell.paragraphs[0]
                run = p.add_run()
                run.add_picture(img_path, width=Inches(img_width_in))
            else:
                cell.text = "(cannot capture)"

    doc.save(save_path)


def export_report_pdf(save_path: str, title: str, system_widget) -> None:
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(f"Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))

    temp_dir = _safe_temp_dir()
    matrix = _build_widget_matrix(system_widget)

    rows = len(matrix)
    cols = len(matrix[0]) if rows else 1

    # A4: lắp đầy bề ngang (trừ margin), không viền
    total_w = 7.2 * inch
    col_w = total_w / max(cols, 1)

    table_data = []
    for r in range(rows):
        row_cells = []
        for c in range(cols):
            w = matrix[r][c]
            if w is None:
                row_cells.append("")
                continue

            get_content = getattr(w, "get_content", None)
            if callable(get_content):
                txt = (get_content() or "").strip()
                row_cells.append(Paragraph(txt.replace("\n", "<br/>"), styles["BodyText"]) if txt else "")
                continue

            img_path = os.path.join(temp_dir, f"cell_r{r+1}_c{c+1}.png")
            ok = _grab_widget_png(w, img_path)
            if ok and os.path.exists(img_path):
                row_cells.append(_pdf_image_fit_page(img_path, col_w))
            else:
                row_cells.append(Paragraph("(cannot capture)", styles["BodyText"]))
        table_data.append(row_cells)

    t = Table(table_data, colWidths=[col_w] * cols)
    # Không GRID/viền, padding tối thiểu để nội dung lắp đầy
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t)

    doc = SimpleDocTemplate(save_path, pagesize=A4)
    doc.build(story)