from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from project1_main_tab.Predict_modules.AAKR_predict import AAKR_predict
from project1_main_tab.Forecasting_modules.forecasting_tab import ForecastingTab


class PredictTab(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self._parent_main = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Tab 1: AAKR (chức năng có sẵn)
        self.aakr_widget = AAKR_predict(parent_main_window=parent)
        self._tabs.addTab(self.aakr_widget, "AAKR")

        # Tab 2: Forecasting (dự đoán tương lai)
        self.forecast_widget = ForecastingTab(
            df_provider=lambda: getattr(self._parent_main, "final_df", None)
        )
        self._tabs.addTab(self.forecast_widget, "Forecasting")

    def update_variables(self, df):
        if hasattr(self.aakr_widget, "update_df_list"):
            self.aakr_widget.update_df_list()
