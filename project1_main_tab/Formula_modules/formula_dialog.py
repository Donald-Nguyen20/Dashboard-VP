# formula_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QHBoxLayout, QScrollArea, QWidget, QMessageBox
)
import json, os

class BuildFormulaDialog(QDialog):
    def __init__(self, main_window=None):
        super().__init__()
        self.setWindowTitle("Build Custom Formula")
        self.setMinimumSize(1000, 500)
        self.main_window = main_window

        self.layout = QVBoxLayout(self)
        self.combo_df = QComboBox()
        self.combo_df.addItems(main_window.get_df_list())  # <-- dùng MainWindow của bạn
        self.combo_df.currentTextChanged.connect(self.update_column_buttons)
        self.layout.addWidget(QLabel("🔹 Chọn DataFrame:"))
        self.layout.addWidget(self.combo_df)

        self.layout.addWidget(QLabel("📌 Chọn cột:"))
        self.column_scroll = QScrollArea()
        self.column_scroll.setWidgetResizable(True)
        self.column_container = QWidget()
        self.column_buttons_layout = QHBoxLayout(self.column_container)
        self.column_scroll.setWidget(self.column_container)
        self.layout.addWidget(self.column_scroll)
        self.operators_layout = QHBoxLayout()
        self.layout.addWidget(QLabel("➕ Toán tử hỗ trợ (bấm để thêm):"))
        self.layout.addLayout(self.operators_layout)
        self.add_operator_buttons()
        self.layout.addWidget(QLabel("✍️ Nhập công thức:"))
        self.input_formula = QLineEdit()
        self.layout.addWidget(self.input_formula)

        self.layout.addWidget(QLabel("⚠️ Điều kiện cảnh báo (VD: `Pressure` > 100):"))
        self.input_alert = QLineEdit()
        self.layout.addWidget(self.input_alert)

        self.layout.addWidget(QLabel("📁 Tên công thức để lưu:"))
        self.input_name = QLineEdit()
        self.layout.addWidget(self.input_name)

        self.btn_create = QPushButton("📤 Tạo và lưu công thức")
        self.btn_create.clicked.connect(self.create_formula)
        self.layout.addWidget(self.btn_create)

        self.update_column_buttons()

    def update_column_buttons(self):
        for i in reversed(range(self.column_buttons_layout.count())):
            self.column_buttons_layout.itemAt(i).widget().deleteLater()

        df_name = self.combo_df.currentText().split(" (")[0]
        df = self.main_window.get_df_by_name(df_name)
        if hasattr(df, 'df'):  # nếu là holder object
            df = df.df
        if df is not None:
            for col in df.columns:
                btn = QPushButton(col)
                btn.setStyleSheet("background-color: lightblue;")
                btn.clicked.connect(lambda _, c=col: self.insert_into_formula(f"`{c}`"))
                self.column_buttons_layout.addWidget(btn)

    def insert_into_formula(self, text):
        cur = self.input_formula.cursorPosition()
        t = self.input_formula.text()
        self.input_formula.setText(t[:cur] + text + t[cur:])
        self.input_formula.setCursorPosition(cur + len(text))

    def add_operator_buttons(self):
        for op in ['+', '-', '*', '/', '(', ')', '=', '`', '>', '<', '>=', '<=', '!=', '==']:
            btn = QPushButton(op)
            btn.setStyleSheet("background-color: lightgray; color: #000;")
            btn.clicked.connect(lambda _, o=op: self.insert_into_formula(o))
            self.operators_layout.addWidget(btn)

    def create_formula(self):
        name = self.input_name.text().strip()
        formula = self.input_formula.text().strip()
        condition = self.input_alert.text().strip()
        df_name = self.combo_df.currentText().split(" (")[0]

        if not name or not formula:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên và công thức.")
            return

        data = {
            "df": df_name,
            "formula_name": name,
            "formula": formula,
            "alert_condition": condition
        }

        os.makedirs("formulas", exist_ok=True)
        path = os.path.join("formulas", f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        QMessageBox.information(self, "Đã lưu", f"✅ Công thức đã lưu tại:\n{path}")
        self.accept()
