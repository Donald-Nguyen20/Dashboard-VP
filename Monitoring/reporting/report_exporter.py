from __future__ import annotations
import os
import datetime as dt
from typing import List, Optional

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QPixmap

# Word
from docx import Document
from docx.shared import Inches

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors


def _safe_temp_dir() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
    out = os.path.join(base, "dashboard_reports")
    os.makedirs(out, exist_ok=True)
    return out


def _grab_widget_png(widget, out_path: str) -> bool:
    if widget is None:
        return False

    # 1) Ưu tiên: matplotlib figure (PlotBoundCell) -> ảnh cực nét
    if _save_plotboundcell_figure(widget, out_path, dpi=300):
        return True

    # 2) Fallback: chụp widget (note/khác) -> có thể mờ hơn
    try:
        pix: QPixmap = widget.grab()
        if pix.isNull():
            return False
        return pix.save(out_path, "PNG")
    except Exception:
        return False
def _save_plotboundcell_figure(widget, out_path: str, dpi: int = 300) -> bool:
    """
    Nếu widget là PlotBoundCell (hoặc có .figure là matplotlib Figure),
    xuất ảnh trực tiếp từ figure để nét (không dùng grab()).
    """
    fig = getattr(widget, "figure", None)
    if fig is None:
        return False
    savefig = getattr(fig, "savefig", None)
    if not callable(savefig):
        return False
    try:
        fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
        return True
    except Exception:
        return False

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


def export_report_docx(save_path: str, title: str, system_widget) -> None:
    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(f"Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph("")

    temp_dir = _safe_temp_dir()
    matrix = _build_widget_matrix(system_widget)

    rows = len(matrix)
    cols = len(matrix[0]) if rows else 1

    # Bề ngang trang Word an toàn khoảng ~6.5 inch (tùy margin), chia theo số cột
    usable_width_in = 6.5
    img_width_in = max(1.2, usable_width_in / max(cols, 1) - 0.1)

    table = doc.add_table(rows=rows, cols=cols)
    table.style = "Table Grid"
    table.autofit = False
    col_width = Inches(6.5 / max(cols, 1))
    for col in table.columns:
        for cell in col.cells:
            cell.width = col_width

    for r in range(rows):
        for c in range(cols):
            cell = table.cell(r, c)
            w = matrix[r][c]

            # Nếu ô không tồn tại (hàng ngắn hơn) → để trống nhẹ
            if w is None:
                cell.text = ""
                continue

            # Note cell: ưu tiên get_content()
            get_content = getattr(w, "get_content", None)
            if callable(get_content):
                text = (get_content() or "").strip()
                cell.text = text if text else ""
                continue

            # Plot/Widget khác: chụp ảnh widget
            img_path = os.path.join(temp_dir, f"cell_r{r+1}_c{c+1}.png")
            ok = _grab_widget_png(w, img_path)
            if ok and os.path.exists(img_path):
                # Clear text, rồi add ảnh
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

    # A4 width ~ 8.27in; trừ margin mặc định của SimpleDocTemplate sẽ còn ~7.2in
    # Ta set colWidths dựa trên ~7.2in
    total_w = 7.2 * inch
    col_w = total_w / max(cols, 1)

    table_data = []
    for r in range(rows):
        row_cells = []
        for c in range(cols):
            w = matrix[r][c]
            if w is None:
                row_cells.append("")  # ô không tồn tại
                continue

            get_content = getattr(w, "get_content", None)
            if callable(get_content):
                txt = (get_content() or "").strip()
                row_cells.append(Paragraph(txt.replace("\n", "<br/>"), styles["BodyText"]) if txt else "")
                continue

            img_path = os.path.join(temp_dir, f"cell_r{r+1}_c{c+1}.png")
            ok = _grab_widget_png(w, img_path)
            if ok and os.path.exists(img_path):
                # chiều cao ảnh cố định để bảng không quá cao
                row_cells.append(RLImage(img_path, width=col_w - 6, height=2.2 * inch))
            else:
                row_cells.append(Paragraph("(cannot capture)", styles["BodyText"]))
        table_data.append(row_cells)

    t = Table(table_data, colWidths=[col_w] * cols)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    doc = SimpleDocTemplate(save_path, pagesize=A4)
    doc.build(story)