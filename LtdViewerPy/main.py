"""
LtdViewerPy – GUI PySide6 tối giản, làm lại chức năng "đọc DSH + xuất CSV".

Workflow:
    1. Chọn thư mục TREND (chứa các file HD????????_??????GMT.DSH)
    2. App tự liệt kê DSH và toàn bộ tag (gộp từ tất cả file)
    3. Người dùng tick chọn tag, chọn khoảng từ–đến và sampling rate
    4. Nhấn "Export CSV"  → file CSV chuẩn LtdViewer

Tab "Inspect" để xem nhanh metadata 1 file DSH (debug/format).
"""

from __future__ import annotations

import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QDateTime, Signal, QObject
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QDateTimeEdit, QMessageBox, QTabWidget, QPlainTextEdit,
    QProgressBar, QAbstractItemView,
)

from .dsh_reader import DshFile, TrendFolderReader, TagInfo
from .csv_exporter import (
    SAMPLING_RATES_SEC, ExportRequest, export_trend_csv,
)


# --- helpers --------------------------------------------------------------
def qdt_to_utc(qdt: QDateTime) -> datetime:
    """Convert a QDateTime (any spec) to a tz-aware UTC datetime.

    QDateTimeEdit hiển thị/edit theo Qt.LocalTime mặc định, nên dù ta khởi tạo
    bằng Qt.UTC, giá trị đọc lại có thể là LocalTime. Cách an toàn nhất là dùng
    toSecsSinceEpoch() — luôn trả unix seconds đúng theo timezone gốc của QDateTime.
    """
    return datetime.fromtimestamp(qdt.toSecsSinceEpoch(), tz=timezone.utc)


# --- export worker --------------------------------------------------------
class ExportWorker(QObject):
    progress = Signal(float)
    finished = Signal(int, str)   # rows, error_msg ('' nếu OK)

    def __init__(self, request: ExportRequest, folder: TrendFolderReader):
        super().__init__()
        self._req = request
        self._folder = folder

    def run(self):
        try:
            rows = export_trend_csv(
                self._req,
                self._folder,
                progress=lambda p: self.progress.emit(p),
            )
            self.finished.emit(rows, "")
        except Exception as e:
            self.finished.emit(0, f"{e}\n\n{traceback.format_exc()}")


# --- main window ----------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LtdViewerPy – DSH → CSV")
        self.resize(1024, 720)
        self._folder: TrendFolderReader | None = None
        self._all_tags: dict[str, TagInfo] = {}

        tabs = QTabWidget()
        tabs.addTab(self._build_export_tab(), "Export CSV")
        tabs.addTab(self._build_inspect_tab(), "Inspect DSH")
        self.setCentralWidget(tabs)

    # ===== Tab 1: Export =====
    def _build_export_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        # --- Path selector ---
        row = QHBoxLayout()
        row.addWidget(QLabel("TREND folder:"))
        self.ed_folder = QLineEdit()
        self.ed_folder.setReadOnly(True)
        row.addWidget(self.ed_folder, 1)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self.on_browse_folder)
        row.addWidget(btn_browse)
        btn_reload = QPushButton("Reload")
        btn_reload.clicked.connect(self.on_reload)
        row.addWidget(btn_reload)
        layout.addLayout(row)

        # --- Tag table ---
        layout.addWidget(QLabel("Tag list (tick các tag muốn xuất):"))
        self.tbl_tags = QTableWidget(0, 6)
        self.tbl_tags.setHorizontalHeaderLabels(
            ["✓", "Tag name", "Description", "Units", "Range", "Decimal"]
        )
        self.tbl_tags.horizontalHeader().setStretchLastSection(False)
        self.tbl_tags.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_tags.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_tags.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.tbl_tags, 1)

        # --- Filter row ---
        f_row = QHBoxLayout()
        f_row.addWidget(QLabel("Filter tag:"))
        self.ed_filter = QLineEdit()
        self.ed_filter.textChanged.connect(self._apply_filter)
        f_row.addWidget(self.ed_filter, 1)
        btn_all = QPushButton("Select all")
        btn_all.clicked.connect(lambda: self._set_all_checks(True))
        f_row.addWidget(btn_all)
        btn_none = QPushButton("Clear all")
        btn_none.clicked.connect(lambda: self._set_all_checks(False))
        f_row.addWidget(btn_none)
        layout.addLayout(f_row)

        # --- Span / sampling / save ---
        grid = QGridLayout()
        grid.addWidget(QLabel("From (UTC):"), 0, 0)
        self.dt_from = QDateTimeEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_from.setTimeSpec(Qt.UTC)   # khoá widget ở UTC để tránh lệch giờ
        grid.addWidget(self.dt_from, 0, 1)

        grid.addWidget(QLabel("To (UTC):"), 0, 2)
        self.dt_to = QDateTimeEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_to.setTimeSpec(Qt.UTC)
        grid.addWidget(self.dt_to, 0, 3)

        grid.addWidget(QLabel("Sampling:"), 1, 0)
        self.cb_sampling = QComboBox()
        for k in SAMPLING_RATES_SEC.keys():
            self.cb_sampling.addItem(k)
        self.cb_sampling.setCurrentText("10sec")
        grid.addWidget(self.cb_sampling, 1, 1)

        grid.addWidget(QLabel("Group name:"), 1, 2)
        self.ed_group = QLineEdit("Group1")
        grid.addWidget(self.ed_group, 1, 3)

        grid.addWidget(QLabel("Save to:"), 2, 0)
        self.ed_save = QLineEdit()
        grid.addWidget(self.ed_save, 2, 1, 1, 2)
        btn_save_browse = QPushButton("Browse…")
        btn_save_browse.clicked.connect(self.on_browse_save)
        grid.addWidget(btn_save_browse, 2, 3)

        layout.addLayout(grid)

        # --- Run row ---
        run_row = QHBoxLayout()
        self.btn_export = QPushButton("Export CSV")
        self.btn_export.clicked.connect(self.on_export)
        run_row.addWidget(self.btn_export)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        run_row.addWidget(self.progress_bar, 1)
        layout.addLayout(run_row)

        self.lbl_status = QLabel("Sẵn sàng.")
        layout.addWidget(self.lbl_status)
        return w

    # ===== Tab 2: Inspect =====
    def _build_inspect_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        row = QHBoxLayout()
        btn = QPushButton("Open DSH file…")
        btn.clicked.connect(self.on_inspect)
        row.addWidget(btn)
        row.addStretch(1)
        layout.addLayout(row)
        self.txt_inspect = QPlainTextEdit()
        self.txt_inspect.setReadOnly(True)
        self.txt_inspect.setStyleSheet("font-family: Consolas, monospace;")
        layout.addWidget(self.txt_inspect, 1)
        return w

    # ===== Slots =====
    def on_browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Chọn thư mục TREND")
        if d:
            self.ed_folder.setText(d)
            self._load_folder(d)

    def on_reload(self):
        if self.ed_folder.text():
            self._load_folder(self.ed_folder.text())

    def on_browse_save(self):
        p, _ = QFileDialog.getSaveFileName(
            self, "Lưu CSV", "trend.csv", "CSV files (*.csv);;All files (*.*)"
        )
        if p:
            self.ed_save.setText(p)

    def _load_folder(self, d: str):
        self._folder = TrendFolderReader(d)
        files = self._folder.files
        self.lbl_status.setText(f"Đã quét {len(files)} file DSH.")
        # Gom tag từ TẤT CẢ file → set tag duy nhất (theo tag_name)
        seen: dict[str, TagInfo] = {}
        for fp in files:
            try:
                dsh = DshFile(fp)
            except Exception:
                continue
            try:
                for t in dsh.iter_tags():
                    if t.tag_name and t.tag_name not in seen:
                        seen[t.tag_name] = t
            finally:
                dsh.close()
        self._all_tags = seen
        self._populate_tags(sorted(seen.keys()))
        # Auto-set thời gian dựa trên header file đầu/cuối
        if files:
            try:
                first = DshFile(files[0]); last = DshFile(files[-1])
                self.dt_from.setDateTime(QDateTime.fromSecsSinceEpoch(first.header.begin_time, Qt.UTC))
                self.dt_to.setDateTime(QDateTime.fromSecsSinceEpoch(last.header.end_time, Qt.UTC))
                first.close(); last.close()
            except Exception:
                pass

    def _populate_tags(self, names: list[str]):
        self.tbl_tags.setRowCount(0)
        for n in names:
            t = self._all_tags[n]
            row = self.tbl_tags.rowCount()
            self.tbl_tags.insertRow(row)
            cb = QTableWidgetItem()
            cb.setFlags(cb.flags() | Qt.ItemIsUserCheckable)
            cb.setCheckState(Qt.Unchecked)
            self.tbl_tags.setItem(row, 0, cb)
            self.tbl_tags.setItem(row, 1, QTableWidgetItem(n))
            self.tbl_tags.setItem(row, 2, QTableWidgetItem(t.description))
            self.tbl_tags.setItem(row, 3, QTableWidgetItem(t.units))
            self.tbl_tags.setItem(row, 4, QTableWidgetItem(f"{t.disp_range_lower:g} … {t.disp_range_upper:g}"))
            self.tbl_tags.setItem(row, 5, QTableWidgetItem(str(t.decimal_place)))
        self.tbl_tags.resizeColumnsToContents()

    def _apply_filter(self, text: str):
        text = text.lower()
        for r in range(self.tbl_tags.rowCount()):
            name = self.tbl_tags.item(r, 1).text().lower()
            desc = self.tbl_tags.item(r, 2).text().lower()
            self.tbl_tags.setRowHidden(r, text not in name and text not in desc)

    def _set_all_checks(self, val: bool):
        state = Qt.Checked if val else Qt.Unchecked
        for r in range(self.tbl_tags.rowCount()):
            if self.tbl_tags.isRowHidden(r):
                continue
            self.tbl_tags.item(r, 0).setCheckState(state)

    def _selected_tags(self) -> list[str]:
        out = []
        for r in range(self.tbl_tags.rowCount()):
            if self.tbl_tags.item(r, 0).checkState() == Qt.Checked:
                out.append(self.tbl_tags.item(r, 1).text())
        return out

    def on_export(self):
        if self._folder is None:
            QMessageBox.warning(self, "Chưa chọn folder", "Hãy chọn thư mục TREND trước.")
            return
        tags = self._selected_tags()
        if not tags:
            QMessageBox.warning(self, "Chưa chọn tag", "Hãy tick ít nhất 1 tag.")
            return
        save_to = self.ed_save.text().strip()
        if not save_to:
            QMessageBox.warning(self, "Chưa chọn nơi lưu", "Hãy chọn đường dẫn file CSV.")
            return

        start = qdt_to_utc(self.dt_from.dateTime())
        end = qdt_to_utc(self.dt_to.dateTime())
        if end <= start:
            QMessageBox.warning(self, "Khoảng thời gian sai", "To phải lớn hơn From.")
            return
        sampling = SAMPLING_RATES_SEC[self.cb_sampling.currentText()]

        req = ExportRequest(
            output_path=Path(save_to),
            group_name=self.ed_group.text() or "Group1",
            start=start, end=end,
            sampling_sec=sampling,
            tags=tags,
        )

        self.btn_export.setEnabled(False)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Đang xuất CSV…")

        worker = ExportWorker(req, self._folder)
        worker.progress.connect(lambda p: self.progress_bar.setValue(int(p * 100)))
        worker.finished.connect(self._on_export_finished)
        self._worker = worker  # giữ reference
        threading.Thread(target=worker.run, daemon=True).start()

    def _on_export_finished(self, rows: int, error: str):
        self.btn_export.setEnabled(True)
        if error:
            self.lbl_status.setText("Xuất CSV thất bại.")
            QMessageBox.critical(self, "CSV export failed", error)
        else:
            self.lbl_status.setText(f"Xuất CSV thành công: {rows} dòng dữ liệu.")
            QMessageBox.information(self, "CSV export succeeded",
                                    f"Đã ghi {rows} dòng dữ liệu vào file.")

    def on_inspect(self):
        p, _ = QFileDialog.getOpenFileName(self, "Mở DSH", "", "DSH files (*.DSH *.dsh)")
        if not p:
            return
        try:
            dsh = DshFile(p)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            return
        try:
            h = dsh.header
            lines = [
                f"File:         {p}",
                f"file_id:      {h.file_id!r}",
                f"file_title:   {h.file_title!r}",
                f"begin_time:   {h.begin_time}  ({h.begin_dt.isoformat()})",
                f"end_time:     {h.end_time}  ({h.end_dt.isoformat()})",
                f"tag_count:    {h.tag_count}",
                f"all_records:  {h.all_record_count}",
                f"file_status:  0x{h.file_status:08X}",
                f"sortedTags:   {h.is_sorted_tag_info}",
                "",
                f"Tag preview (top 50):",
                f"{'idx':<6}{'tagName':<32}{'units':<12}{'records':>10}  description",
            ]
            for tag in list(dsh.iter_tags())[:50]:
                lines.append(
                    f"{tag.index:<6}{tag.tag_name:<32}{tag.units:<12}{tag.record_count:>10}  {tag.description}"
                )
            self.txt_inspect.setPlainText("\n".join(lines))
        finally:
            dsh.close()


# --- entry ---------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
