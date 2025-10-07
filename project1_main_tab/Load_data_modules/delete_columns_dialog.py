# delete_columns_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QPushButton, QScrollArea, QWidget, QHBoxLayout, QMessageBox

class DeleteColumnsDialog(QDialog):
    def __init__(self, df_owner, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🧹 Delete Unused Features")
        self.resize(400, 400)

        self.df_owner = df_owner  # PreviewDialog hoặc đối tượng chứa .df_full

        layout = QVBoxLayout(self)

        # 👉 Scroll area chứa danh sách checkbox
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.checkbox_layout = QVBoxLayout(scroll_content)

        self.checkboxes = []
        for col in self.df_owner.df_full.columns:
            cb = QCheckBox(col)
            self.checkboxes.append(cb)
            self.checkbox_layout.addWidget(cb)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # 👉 Nút xác nhận và hủy
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")
        btn_ok.clicked.connect(self.apply_delete)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def apply_delete(self):
        cols_to_drop = [cb.text() for cb in self.checkboxes if cb.isChecked()]
        if not cols_to_drop:
            QMessageBox.information(self, "Thông báo", "Bạn chưa chọn cột nào để xóa.")
            return

        self.df_owner.df_full.drop(columns=cols_to_drop, inplace=True)
        self.accept()
