# timeline_filter.py
from PySide6.QtWidgets import QHBoxLayout, QLabel, QDateTimeEdit
from PySide6.QtCore import QDateTime
import pandas as pd

def create_datetime_filter_controls(df: pd.DataFrame, on_change_callback=None):
    layout = QHBoxLayout()

    label_from = QLabel("Từ:")
    start_edit = QDateTimeEdit()
    start_edit.setCalendarPopup(True)
    start_edit.setDisplayFormat("dd/MM/yyyy HH:mm:ss")

    label_to = QLabel("Đến:")
    end_edit = QDateTimeEdit()
    end_edit.setCalendarPopup(True)
    end_edit.setDisplayFormat("dd/MM/yyyy HH:mm:ss")

    if 'Datetime' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Datetime']):
        valid_times = df['Datetime'].dropna()
        if not valid_times.empty:
            min_time = valid_times.min().to_pydatetime()
            max_time = valid_times.max().to_pydatetime()
        else:
            now = pd.Timestamp.now()
            min_time = max_time = now

        start_edit.setDateTime(QDateTime(min_time))
        end_edit.setDateTime(QDateTime(max_time))


    # Gắn callback để update khi thay đổi
    if on_change_callback:
        start_edit.dateTimeChanged.connect(lambda _: on_change_callback())
        end_edit.dateTimeChanged.connect(lambda _: on_change_callback())


    layout.addWidget(label_from)
    layout.addWidget(start_edit)
    layout.addWidget(label_to)
    layout.addWidget(end_edit)

    return layout, start_edit, end_edit

def filter_dataframe_by_datetime(df: pd.DataFrame, start_dt, end_dt):
    try:
        return df[(df["Datetime"] >= start_dt) & (df["Datetime"] <= end_dt)]
    except Exception as e:
        print(f"⚠️ Lỗi khi lọc thời gian: {e}")
        return df
