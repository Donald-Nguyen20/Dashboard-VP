from PySide6.QtWidgets import QWidget, QVBoxLayout
from project1_main_tab.Predict_modules.AAKR_predict import AAKR_predict

class PredictTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        layout = QVBoxLayout(self)
        self.aakr_widget = AAKR_predict(parent_main_window=parent)
        layout.addWidget(self.aakr_widget)

    def update_variables(self, df):
        # Gọi update_df_list để refresh danh sách DataFrame và các biến cột
        if hasattr(self.aakr_widget, "update_df_list"):
            self.aakr_widget.update_df_list()