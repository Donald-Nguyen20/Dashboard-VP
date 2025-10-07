# data_cleaning_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton
from PySide6.QtCore import Qt
import pandas as pd



class DataCleaningDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Data Cleaning")
        self.setMinimumSize(250, 150)
        self.parent = parent
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)

        self.combo_df = QComboBox()
        self.combo_df.addItems(self.parent.get_df_list())

        self.combo_col = QComboBox()
        self.combo_op = QComboBox()
        self.combo_op.addItems([">", "<", ">=", "<=", "==", "!=", "within"])

        self.input_val1 = QLineEdit()
        self.input_val2 = QLineEdit()
        self.input_val2.setPlaceholderText("Giá trị trên (chỉ khi chọn 'within')")
        self.input_val2.hide()

        self.combo_df.currentTextChanged.connect(self.update_columns)
        self.combo_op.currentTextChanged.connect(self.toggle_val2)
        self.update_columns()

        btn_apply = QPushButton("Áp dụng lọc")
        btn_apply.clicked.connect(self.apply_filter)

        layout.addWidget(QLabel("Chọn DF:"))
        layout.addWidget(self.combo_df)
        layout.addWidget(QLabel("Chọn Cột:"))
        layout.addWidget(self.combo_col)
        layout.addWidget(QLabel("Toán tử:"))
        layout.addWidget(self.combo_op)
        layout.addWidget(QLabel("Giá trị:"))
        layout.addWidget(self.input_val1)
        layout.addWidget(self.input_val2)
        layout.addWidget(btn_apply)

    def update_columns(self):
        df_name = self.combo_df.currentText().split(" (")[0]
        df = self.parent.get_df_by_name(df_name)
        self.combo_col.clear()
        if isinstance(df, pd.DataFrame):
            self.combo_col.addItems(df.columns.astype(str).tolist())
        elif hasattr(df, "df"):
            self.combo_col.addItems(df.df.columns.astype(str).tolist())



    def toggle_val2(self):
        self.input_val2.setVisible(self.combo_op.currentText().lower() == "within")

    def apply_filter(self):
        df_name = self.combo_df.currentText().split(" (")[0]
        df_button = self.parent.get_df_by_name(df_name)

        # ✅ Kiểm tra kiểu và lấy DataFrame phù hợp
        if df_button is None:
            print("❌ Không tìm thấy DF.")
            return

        if isinstance(df_button, pd.DataFrame):
            working_df = df_button
        elif hasattr(df_button, "df"):
            working_df = df_button.df
        else:
            print("❌ Không xác định được DataFrame.")
            return

        col = self.combo_col.currentText()
        op = self.combo_op.currentText()

        try:
            val1 = float(self.input_val1.text())
            val2 = float(self.input_val2.text()) if op == "within" else None
        except ValueError:
            print("❌ Giá trị nhập không hợp lệ!")
            return

        try:
            if op == ">":
                mask = working_df[col] > val1
            elif op == "<":
                mask = working_df[col] < val1
            elif op == ">=":
                mask = working_df[col] >= val1
            elif op == "<=":
                mask = working_df[col] <= val1
            elif op == "==":
                mask = working_df[col] == val1
            elif op == "!=":
                mask = working_df[col] != val1
            elif op == "within":
                mask = (working_df[col] >= val1) & (working_df[col] <= val2)
            else:
                print("❌ Toán tử không hợp lệ.")
                return

            # ✅ Lọc và cập nhật kết quả
            cleaned = working_df[~mask].reset_index(drop=True)
            print(f"✅ Đã lọc bỏ theo điều kiện: {col} {op} {val1}")
            print(cleaned.head())

            self.cleaned_df = cleaned
            self.accept()

        except Exception as e:
            print(f"❌ Lỗi khi lọc: {e}")

    def get_cleaned_data(self):
        return getattr(self, "cleaned_df", None)



