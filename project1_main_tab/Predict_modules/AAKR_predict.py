from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from PySide6.QtWidgets import QDateTimeEdit
from PySide6.QtCore import QDateTime


class AAKR_predict(QWidget):
    def __init__(self, parent_main_window=None):
        super().__init__()
        self.parent = parent_main_window
        self.init_ui()
        self.update_df_list()
        self.predicted_result_df = None

    def init_ui(self):
        layout = QVBoxLayout(self)
        header = QLabel("🔮 AAKR Predict - rolling window (train & predict)")
        header.setStyleSheet("font-weight: bold; font-size: 17px;")
        layout.addWidget(header)

        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("Chọn DataFrame:"))
        self.combo_df = QComboBox()
        hlayout.addWidget(self.combo_df)

        hlayout.addWidget(QLabel("Days for training:"))
        self.input_train_days = QLineEdit("30")
        self.input_train_days.setMaximumWidth(90)
        hlayout.addWidget(self.input_train_days)

        hlayout.addWidget(QLabel("From (predict):"))
        self.input_start_time = QDateTimeEdit()
        self.input_start_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.input_start_time.setCalendarPopup(True)
        hlayout.addWidget(self.input_start_time)

        hlayout.addWidget(QLabel("To (predict):"))
        self.input_end_time = QDateTimeEdit()
        self.input_end_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.input_end_time.setCalendarPopup(True)
        hlayout.addWidget(self.input_end_time)


        self.btn_predict = QPushButton("🔮 Predict")
        self.btn_predict.clicked.connect(self.predict_all)
        hlayout.addWidget(self.btn_predict)

        layout.addLayout(hlayout)
        self.table = QTableWidget()
        layout.addWidget(self.table)

        self.combo_df.currentTextChanged.connect(self.update_columns)
        self.combo_col = QComboBox()  # Không dùng nhưng giữ cấu trúc nếu cần mở rộng


        hlayout.addWidget(QLabel("K-nearest neighbors:"))
        self.input_k = QLineEdit("10")
        self.input_k.setMaximumWidth(50)
        hlayout.addWidget(self.input_k)


    def update_df_list(self):
        self.combo_df.blockSignals(True)
        self.combo_df.clear()
        if self.parent is not None and hasattr(self.parent, "get_df_list"):
            df_list = self.parent.get_df_list()
            self.combo_df.addItems(df_list)
        self.combo_df.blockSignals(False)
        self.update_columns()

    def update_columns(self):
        df = self.get_current_df()
        self.combo_col.clear()
        if df is not None and isinstance(df, pd.DataFrame):
            numeric_cols = [c for c in df.columns if c not in ["Datetime"] and pd.api.types.is_numeric_dtype(df[c])]
            self.combo_col.addItems(numeric_cols)
            # Thiết lập mốc thời gian mặc định
            if "Datetime" in df.columns and not df["Datetime"].isnull().all():
                df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")
                df = df.dropna(subset=["Datetime"])

                if not df.empty:
                    min_time = df["Datetime"].min()
                    max_time = df["Datetime"].max()
                    self._set_default_predict_last_30_days(min_time, max_time)


    def _set_default_predict_last_30_days(self, min_time, max_time):
        # convert to python datetime
        max_dt = pd.to_datetime(max_time).to_pydatetime()
        min_dt = pd.to_datetime(min_time).to_pydatetime()

        start_30 = (pd.Timestamp(max_dt) - pd.Timedelta(days=30)).to_pydatetime()
        start_dt = max(start_30, min_dt)  # nếu data < 30 ngày thì bám min

        # CHỈ set giá trị hiển thị (default), KHÔNG set min/max để khỏi khóa user
        self.input_start_time.setDateTime(QDateTime(start_dt))
        self.input_end_time.setDateTime(QDateTime(max_dt))

    def get_current_df(self):
        df_fullname = self.combo_df.currentText()
        if not df_fullname:
            return None
        df_key = df_fullname.split(" (")[0]
        if hasattr(self.parent, "get_df_by_name"):
            df = self.parent.get_df_by_name(df_key)
            if isinstance(df, pd.DataFrame):
                return df
            if hasattr(df, "df"):
                return df.df
        if hasattr(self.parent, "dataframes") and df_key in self.parent.dataframes:
            df = self.parent.dataframes[df_key]
            if isinstance(df, pd.DataFrame):
                return df
            if hasattr(df, "df"):
                return df.df
        if df_key.startswith("MergedData") and hasattr(self.parent, "final_df"):
            return self.parent.final_df
        return None

    def predict_all(self):
        self.table.clear()
        df = self.get_current_df()
        if df is None or df.empty:
            QMessageBox.warning(self, "Data is empty", "No DataFrame.")
            return

        try:
            train_days = int(self.input_train_days.text())
            k = int(self.input_k.text())
            if train_days < 1 or k < 1:
                raise ValueError()

        except Exception:
            QMessageBox.warning(self, "Input value is wrong", "Train days and k must be positive integers.")
            return

        # Yêu cầu cột "Datetime"
        if "Datetime" not in df.columns:
            QMessageBox.warning(self, "Thiếu cột Datetime", "DataFrame phải có cột 'Datetime' (kiểu ngày giờ).")
            return

        # Lấy ngày cuối cùng làm mốc
        df = df.copy()
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df = df.sort_values("Datetime")

        try:
            train_days = int(self.input_train_days.text())
            k = int(self.input_k.text())
            if train_days < 1 or k < 1:
                raise ValueError()
        except Exception:
            QMessageBox.warning(self, "Input value is wrong", "Train days and k must be positive integers.")
            return

        # Lấy vùng predict từ QDateTimeEdit
        predict_start = self.input_start_time.dateTime().toPython()
        predict_end = self.input_end_time.dateTime().toPython()
        if predict_end < predict_start:
            QMessageBox.warning(self, "Error", "End date must be greater than or equal to start date.")
            return

        pred_df = df[(df["Datetime"] >= predict_start) & (df["Datetime"] <= predict_end)]

        # Lấy vùng train ngay trước vùng predict
        train_end = predict_start - pd.Timedelta(hours=1)
        train_start = train_end - pd.Timedelta(days=train_days-1)
        train_df = df[(df["Datetime"] >= train_start) & (df["Datetime"] <= train_end)]



        features = [c for c in df.columns if c != "Datetime" and pd.api.types.is_numeric_dtype(df[c])]
        if len(features) < 2:
            QMessageBox.warning(self, "Thiếu biến số học", "DataFrame cần ít nhất 2 biến số học.")
            return

        if len(train_df) < 10:
            QMessageBox.warning(self, "Thiếu dữ liệu train", f"Không đủ dữ liệu để train (>=10 dòng). Có {len(train_df)} dòng.")
            return
        if len(pred_df) == 0:
            QMessageBox.warning(self, "Thiếu dữ liệu predict", "Không có dữ liệu để predict.")
            return

        predicted_df = pred_df[["Datetime"]].copy()
        all_indexes = pred_df.index

        log_lines = []
        for col_predict in features:
            features_for_train = [c for c in features if c != col_predict]
            train_data = train_df[features_for_train + [col_predict]].dropna()
            pred_data = pred_df[features_for_train + [col_predict]].dropna()
            if len(train_data) < 10 or len(pred_data) == 0:
                predicted_df.loc[all_indexes, f"{col_predict}_Thực tế"] = np.nan
                predicted_df.loc[all_indexes, f"{col_predict}_Dự đoán"] = np.nan
                predicted_df.loc[all_indexes, f"{col_predict}_% Sai lệch"] = np.nan
                continue

            scaler = StandardScaler()
            train_X = scaler.fit_transform(train_data[features_for_train].values)
            train_y = train_data[col_predict].values
            pred_X = scaler.transform(pred_data[features_for_train].values)
            real_y = pred_data[col_predict].values

            k = min(k, len(train_X))
            sigma = 1.0
            preds = []
            for x in pred_X:
                dists = np.linalg.norm(train_X - x, axis=1)
                weights = np.exp(-dists ** 2 / (2 * sigma ** 2))
                idx = np.argsort(dists)[:k]
                w = weights[idx]
                if w.sum() == 0:
                    pred = train_y[idx].mean()
                else:
                    w /= w.sum()
                    pred = np.dot(w, train_y[idx])
                preds.append(pred)

            abs_err = np.abs(real_y - np.array(preds))
            pct_err = np.where(real_y != 0, abs_err / np.abs(real_y) * 100, 0)

            pred_index = pred_data.index
            predicted_df.loc[pred_index, f"{col_predict}_Current"] = real_y
            predicted_df.loc[pred_index, f"{col_predict}_Prediction"] = preds
            predicted_df.loc[pred_index, f"{col_predict}_% Deviation"] = pct_err

        # Lưu vào MainWindow
        df_fullname = self.combo_df.currentText()
        if not df_fullname:
            return
        df_key = df_fullname.split(" (")[0]
        predicted_name = f"{df_key}_predicted"
        if hasattr(self.parent, "dataframes"):
            self.parent.dataframes[predicted_name] = predicted_df
        self.predicted_result_df = predicted_df.copy()
        self.show_results(predicted_df)
        QMessageBox.information(self, "Success", f"Created DataFrame '{predicted_name}' with prediction results!")

    def show_results(self, df):
        self.table.clear()
        # Thiết lập lại mốc thời gian cho filter (nếu có cột Datetime)
        if "Datetime" in df.columns and not df["Datetime"].isnull().all():
            df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")
            df = df.dropna(subset=["Datetime"])

            if not df.empty:
                min_time = df["Datetime"].min()
                max_time = df["Datetime"].max()
                self._set_default_predict_last_30_days(min_time, max_time)

        # Chỉ hiển thị 100 dòng mới nhất!
        if len(df) > 100:
            df = df.tail(100)
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels([str(c) for c in df.columns])

        for i in range(len(df)):
            for j, col in enumerate(df.columns):
                val = df.iloc[i, j]
                item = QTableWidgetItem(str(round(val, 4)) if isinstance(val, float) else str(val))
                if "_% Deviation" in col:
                    try:
                        percent = abs(float(val))
                        if percent > 15:
                            item.setForeground(Qt.red)
                            item.setToolTip("🚨 Deviation> 15%")
                        elif percent > 10:
                            item.setForeground(Qt.darkYellow)
                            item.setToolTip("⚠️ Deviation > 10%")
                    except:
                        pass
                self.table.setItem(i, j, item)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

