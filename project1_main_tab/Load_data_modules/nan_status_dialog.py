# project1_main_tab/Load_data_modules/nan_status_dialog.py

import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QHBoxLayout,
    QPushButton, QMessageBox
)


class NaNStatusDialog(QDialog):
    """
    Dialog thống kê NaN theo từng cột và cho phép xóa tất cả các hàng có NaN.
    - Nhận vào: df (DataFrame đầy đủ)
    - Trả ra: cleaned_df (sau khi xóa NaN) qua get_cleaned_df()
    """
    def __init__(self, df: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NaN Status / Delete NaN Rows")
        self.resize(500, 400)

        self._original_df = df
        self._cleaned_df = None

        layout = QVBoxLayout(self)

        # Vùng text hiển thị thống kê NaN
        self.text_report = QTextEdit(self)
        self.text_report.setReadOnly(True)
        layout.addWidget(self.text_report)

        # Hàng button
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.btn_delete = QPushButton("🧹 Delete NaN rows")
        self.btn_delete.clicked.connect(self._on_delete_nan_clicked)
        btn_layout.addWidget(self.btn_delete)

        self.btn_close = QPushButton("Đóng")
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        btn_layout.addStretch()

        # Tính toán & hiển thị thống kê ngay khi mở
        self._build_report()

    def _build_report(self):
        df = self._original_df
        total_rows = len(df)

        if total_rows == 0:
            self.text_report.setPlainText("DataFrame đang trống, không có dòng nào.")
            self.btn_delete.setEnabled(False)
            return

        nan_counts = df.isna().sum()
        cols_with_nan = nan_counts[nan_counts > 0]

        if cols_with_nan.empty:
            self.text_report.setPlainText(
                f"Không có giá trị NaN trong DataFrame.\n\nTổng số dòng: {total_rows}"
            )
            self.btn_delete.setEnabled(False)
            return

        lines = [
            f"Tổng số dòng: {total_rows}",
            "",
            "Các cột có NaN:",
            ""
        ]
        for col, cnt in cols_with_nan.items():
            pct = cnt * 100.0 / total_rows
            lines.append(f"- {col}: {cnt} dòng (~{pct:.2f}%)")

        report = "\n".join(lines)
        self.text_report.setPlainText(report)

    def _on_delete_nan_clicked(self):
        df = self._original_df
        before_rows = len(df)

        # 🔥 Xóa mọi hàng có NaN ở BẤT KỲ cột nào
        cleaned = df.dropna().reset_index(drop=True)
        after_rows = len(cleaned)
        removed = before_rows - after_rows

        if removed <= 0:
            QMessageBox.information(
                self,
                "Delete NaN",
                "Không có dòng nào chứa NaN để xóa.\n"
                "Có thể dữ liệu đã được clean trước đó."
            )
            return

        self._cleaned_df = cleaned

        QMessageBox.information(
            self,
            "Delete NaN",
            f"Đã xóa {removed} dòng có NaN.\n"
            f"Trước: {before_rows} dòng\nSau:   {after_rows} dòng"
        )

        # Đóng dialog và báo thành công
        self.accept()

    def get_cleaned_df(self) -> pd.DataFrame | None:
        """
        Trả về DataFrame đã xóa NaN (nếu user bấm Delete).
        Nếu user chỉ xem rồi Close → trả None.
        """
        return self._cleaned_df
