from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QDialogButtonBox, QGroupBox
)

class ExportReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Report")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        # Title
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Tiêu đề báo cáo:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("VD: BFP Monitoring Report - Unit 1")
        row1.addWidget(self.title_edit, 1)
        layout.addLayout(row1)

        # Format
        group = QGroupBox("Định dạng")
        g_layout = QVBoxLayout(group)
        self.rb_word = QRadioButton("Word (.docx)")
        self.rb_pdf = QRadioButton("PDF (.pdf)")
        self.rb_word.setChecked(True)
        g_layout.addWidget(self.rb_word)
        g_layout.addWidget(self.rb_pdf)
        layout.addWidget(group)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_values(self):
        title = self.title_edit.text()
        fmt = "docx" if self.rb_word.isChecked() else "pdf"
        return title, fmt