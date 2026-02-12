import pandas as pd
from pathlib import Path
import io
from PySide6.QtWidgets import ( QWidget, QVBoxLayout, QPushButton, QTextEdit, QFileDialog, QMessageBox)
from PySide6.QtWidgets import QTableView
from PySide6.QtCore import QAbstractTableModel, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from project1_main_tab.Load_data_modules.nan_status_dialog import NaNStatusDialog


class CsvCleanerWidget(QWidget):
    def __init__(self, parent_main_window=None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.parent_main_window = parent_main_window

    def _get_date_parse_params(self):
        """
        Lấy dayfirst và fmt từ combobox Date format ở MainWindow.
        Default: dd/MM/yyyy HH:MM:SS (VN).
        """
        dayfirst = True
        fmt = "%d/%m/%Y %H:%M:%S"

        pmw = self.parent_main_window
        if pmw is not None and hasattr(pmw, "cb_date_format"):
            cb = pmw.cb_date_format
            idx = cb.currentIndex()
            data = cb.itemData(idx)
            if isinstance(data, dict):
                dayfirst = data.get("dayfirst", dayfirst)
                fmt = data.get("fmt", fmt)

        return dayfirst, fmt

    def select_and_process_files_from_filelist(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn các file để xử lý và gộp ngang",
            "",
            "Dữ liệu (*.csv *.xlsm *.xlsb *.xlsx)"
        )
        if not file_paths:
            QMessageBox.information(self, "Thông báo", "Không có file nào được chọn.")
            return

        dfs = []
        for path_str in file_paths:
            filepath = Path(path_str)
            try:
                df = self.read_flexible_description_csv(filepath)
                df = df.drop(columns=["SourceFile"], errors="ignore")
                dfs.append(df)
            except Exception as e:
                print(f"❌ Lỗi xử lý file {filepath.name}: {e}")

        if not dfs:
            QMessageBox.warning(self, "Cảnh báo", "Không có file hợp lệ để gộp.")
            return

        merged_df = dfs[0]
        for df in dfs[1:]:
            df = df.drop(columns=["SourceFile"], errors="ignore")
            merged_df = pd.merge(merged_df, df, on=["Date", "Time"], how="outer")

        # Xử lý cột Datetime
                # Xử lý cột Datetime
        if 'Datetime' in merged_df.columns:
            merged_df['Datetime'] = pd.to_datetime(merged_df['Datetime'], errors='coerce')
        else:
            # Lấy dayfirst & format từ combobox Date format
            dayfirst, fmt = self._get_date_parse_params()

            merged_df['Datetime'] = pd.to_datetime(
                merged_df['Date'].astype(str).str.strip() + ' ' + merged_df['Time'].astype(str).str.strip(),
                dayfirst=dayfirst,
                format=fmt,
                errors='coerce'
            )

        merged_df = merged_df.sort_values(by='Datetime')
        cols = ['Datetime'] + [col for col in merged_df.columns if col not in ['Date', 'Time', 'Datetime']]
        merged_df = merged_df[cols]
        merged_df.columns = [col.split(" [")[0] if " [" in col else col for col in merged_df.columns]

        # Xuất file cho dễ kiểm soát kết quả
        if file_paths:
            output_file = Path(file_paths[0]).with_name("Data_Loaded.csv")
            merged_df.to_csv(output_file, index=False)
            print(f"\n📁 Đã gộp và lưu file: {output_file.name}")

        # Gán kết quả về main
        if self.parent_main_window:
            self.parent_main_window.set_final_df(merged_df)
        self.df = merged_df
        self.text = lambda: "MergedData"
        self.cell_range = "merged"

        # Preview
        from project1_main_tab.load_data import PreviewWidget
        if hasattr(self, "preview_widget"):
            self.layout().removeWidget(self.preview_widget)
            self.preview_widget.deleteLater()
        df_preview = merged_df.head(100)
        widget = PreviewWidget(df_preview, self)
        widget.df_full = merged_df
        self.preview_widget = widget
        self.layout().addWidget(self.preview_widget)

    def read_flexible_description_csv(self, filepath):
        filepath = Path(filepath)
        suffix = filepath.suffix.lower()

        if suffix == ".csv":
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Nếu đã có cột Date, Time ở dòng đầu tiên => coi như đã xử lý
            if lines[0].strip().lower().startswith('date'):
                df_data = pd.read_csv(filepath)
                return df_data

            # Nếu chưa xử lý -> tiếp tục ánh xạ description
            data_start_idx = None
            for i, line in enumerate(lines):
                if line.strip().lower().startswith('date'):
                    data_start_idx = i
                    break

            if data_start_idx is None:
                raise ValueError(f"Không tìm thấy dòng bắt đầu bằng 'Date' trong file: {filepath.name}")

            df_header = pd.read_csv(filepath, header=None, nrows=data_start_idx, engine='python')
            df_tags = df_header.iloc[2:, [1, 2]].dropna()
            df_tags.columns = ['TagNo', 'Description']

            # 🧽 Loại trùng dựa trên TagNo để tránh lặp giá trị
            df_tags = df_tags.drop_duplicates(subset=['TagNo'])

            descriptions = [f"{desc} [{tag}]" for tag, desc in zip(df_tags['TagNo'], df_tags['Description'])]

            clean_data = "".join(lines[data_start_idx:])
            df_data = pd.read_csv(io.StringIO(clean_data))

            num_data_columns = df_data.shape[1] - 2
            if len(descriptions) < num_data_columns:
                descriptions += [f'Unknown_{i+1}' for i in range(num_data_columns - len(descriptions))]
            else:
                descriptions = descriptions[:num_data_columns]

            df_data.columns = ['Date', 'Time'] + descriptions
            return df_data

        elif suffix in [".xlsm", ".xlsx"]:
            df_data = pd.read_excel(filepath, engine="openpyxl")

            # ✅ Ép định dạng cột Datetime để dùng được với QDateTime
            if 'Datetime' in df_data.columns:
                df_data['Datetime'] = pd.to_datetime(df_data['Datetime'], errors='coerce')

            return df_data


        elif suffix == ".xlsb":
            df_data = pd.read_excel(filepath, engine="pyxlsb")

        else:
            raise ValueError(f"Không hỗ trợ định dạng file: {suffix}")

        # Nếu file Excel đã có cột chuẩn => bỏ qua ánh xạ
        expected_columns = df_data.columns[:2].str.lower().tolist()
        if expected_columns == ['date', 'time']:
            return df_data

        # Nếu chưa chuẩn => tạo cột giả
        num_data_columns = df_data.shape[1] - 2
        descriptions = [f'Col_{i+1}' for i in range(num_data_columns)]
        df_data.columns = ['Date', 'Time'] + descriptions
        return df_data


    def select_and_process_files(self):
        from datetime import datetime
        from project1_main_tab.load_data import PreviewWidget
        import sqlite3

        folder_path = getattr(self, "_external_folder", None)
        if not folder_path:
            folder_path = QFileDialog.getExistingDirectory(
                self, "Chọn thư mục GốC chứa các thư mục con với các file dữ liệu"
            )
        if not folder_path:
            QMessageBox.information(self, "Thông báo", "Không có thư mục nào được chọn.")
            return

        root_folder = Path(folder_path)
        folder_name = root_folder.name
        sqlite_path = root_folder / f"{folder_name}.db"

        conn = sqlite3.connect(sqlite_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                folder_name TEXT PRIMARY KEY,
                processed_time TEXT
            )
        """)

        try:
            existing_folders = set(row[0] for row in conn.execute("SELECT folder_name FROM metadata"))
        except:
            existing_folders = set()

        all_dfs = []
        folder_count = 0
        processed_folders = []

        for subfolder in sorted(root_folder.iterdir()):
            if subfolder.is_dir() and subfolder.name not in existing_folders:
                folder_count += 1
                file_paths = sorted([
                    f for f in subfolder.glob("*") if f.suffix.lower() in [".csv", ".xlsm", ".xlsx", ".xlsb"]
                ])

                dfs = []
                for filepath in file_paths:
                    try:
                        df = self.read_flexible_description_csv(filepath)
                        df = df.drop(columns=["SourceFile"], errors="ignore")
                        dfs.append(df)
                    except Exception as e:
                        print(f"❌ Lỗi xử lý file {filepath.name} trong {subfolder.name}: {e}")

                if dfs:
                    merged_df = dfs[0]
                    for df in dfs[1:]:
                        df = df.drop(columns=["SourceFile"], errors="ignore")
                        merged_df = pd.merge(merged_df, df, on=["Date", "Time"], how="outer")

                    if 'Datetime' not in merged_df.columns:
                        # Lấy dayfirst & format từ combobox Date format
                        dayfirst, fmt = self._get_date_parse_params()

                        merged_df['Datetime'] = pd.to_datetime(
                            merged_df['Date'].astype(str).str.strip() + ' ' + merged_df['Time'].astype(str).str.strip(),
                            dayfirst=dayfirst,
                            format=fmt,
                            errors='coerce'
                        )


                    # 🏷️ Gắn cột SourceFolder riêng biệt để tránh trùng
                    merged_df["__SourceFolder__"] = subfolder.name

                    # ✔️ Làm sạch và chuẩn hoá
                    merged_df.columns = [col.split(" [")[0] if " [" in col else col for col in merged_df.columns]
                    merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
                    merged_df = merged_df.dropna(subset=["Datetime"])
                    merged_df = merged_df.sort_values(by="Datetime")

                    # Loại các cột không cần lưu
                    merged_df = merged_df.drop(columns=["Date", "Time"], errors="ignore")

                    # Ghi vào SQL
                    merged_df.to_sql("data", conn, if_exists="append", index=False)

                    conn.execute(
                        "INSERT OR REPLACE INTO metadata (folder_name, processed_time) VALUES (?, ?)",
                        (subfolder.name, datetime.now().isoformat())
                    )

                    processed_folders.append(subfolder.name)

        conn.commit()
        final_df = pd.read_sql_query("SELECT * FROM data", conn, parse_dates=["Datetime"])
        conn.close()

        if final_df.empty:
            QMessageBox.warning(self, "Không có dữ liệu", "Không tìm thấy dữ liệu trong SQLite hoặc folder mới.")
            return

        final_df = final_df.sort_values(by="Datetime")
        final_df.columns = [col.split(" [")[0] if " [" in col else col for col in final_df.columns]
        final_df = final_df.loc[:, ~final_df.columns.duplicated()]
        cols = ['Datetime'] + [col for col in final_df.columns if col not in ['Datetime']]
        final_df = final_df[cols]

        # 📂 Ghi CSV
        output_file = root_folder / f"{folder_name}.csv"
        final_df.to_csv(output_file, index=False)

        if self.parent_main_window:
            self.parent_main_window.set_final_df(final_df, folder_name=folder_name)
            self.parent_main_window.final_df = final_df

        self.df = final_df
        self.text = lambda: "MergedData"
        self.cell_range = "all_folders"

        # Preview
        if hasattr(self, "preview_widget"):
            self.layout().removeWidget(self.preview_widget)
            self.preview_widget.deleteLater()

        df_preview = final_df.tail(100)
        widget = PreviewWidget(df_preview, self, df_key=folder_name)
        widget.df_full = final_df
        self.preview_widget = widget
        self.layout().addWidget(self.preview_widget)

        print(f"\n📁 Đã xử lý {folder_count} thư mục mới. Đã thêm: {processed_folders}")
        print(f"📆 Tổng {len(final_df)} dòng dữ liệu trong: {sqlite_path.name}")


class PandasModel(QAbstractTableModel):
    def __init__(self, df=pd.DataFrame(), parent=None):
        super().__init__(parent)
        self._df = df

    def rowCount(self, parent=None):
        return len(self._df)

    def columnCount(self, parent=None):
        return self._df.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            value = self._df.iloc[index.row(), index.column()]
            return str(value)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._df.columns[section]).split(" [")[0]

        else:
            return str(section)
        


from project1_main_tab.Load_data_modules.timeline_filter import create_datetime_filter_controls
from project1_main_tab.Load_data_modules.timeline_filter import filter_dataframe_by_datetime
from project1_main_tab.Load_data_modules.data_cleaning_dialog import DataCleaningDialog
from PySide6.QtWidgets import QHBoxLayout
from project1_main_tab.Load_data_modules.delete_columns_dialog import DeleteColumnsDialog
from PySide6.QtWidgets import QSizePolicy 
from PySide6.QtWidgets import QMenu, QToolButton
from project1_main_tab.Formula_modules.formula_dialog import BuildFormulaDialog  
from project1_main_tab.Formula_modules.insert_formula import insert_formula_feature



class PreviewWidget(QWidget):
    def __init__(self, df, parent=None, df_key="MergedData"):
        super().__init__(parent)
        self.df_full = df.copy()
        self.df_key = df_key
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        filter_layout, self.start_time, self.end_time = create_datetime_filter_controls(df)
        filter_layout.setSpacing(10)
        self.start_time.setFixedWidth(180)
        self.end_time.setFixedWidth(180)

        layout.addLayout(filter_layout)
        
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setFixedSize(100, 28)
        self.btn_refresh.clicked.connect(self.update_table)
        filter_layout.addWidget(self.btn_refresh)

        # 👉 Nút Clean Data
        self.btn_clean = QPushButton("🧹 Clean Data")
        self.btn_clean.setFixedSize(120, 28)
        self.btn_clean.clicked.connect(self.open_cleaning_dialog)
        filter_layout.addWidget(self.btn_clean)

        # 👉 Nút NaN Manager
        self.btn_nan = QPushButton("NaN status")
        self.btn_nan.setFixedSize(110, 28)
        self.btn_nan.clicked.connect(self.open_nan_status_dialog)
        filter_layout.addWidget(self.btn_nan)

        self.btn_delete = QPushButton("🗑 Delete Features")
        self.btn_delete.setFixedSize(140, 28)
        self.btn_delete.clicked.connect(self.open_delete_columns_dialog)
        filter_layout.addWidget(self.btn_delete)

        # 📐 Formula Menu
        self.btn_formula_menu = QToolButton()
        self.btn_formula_menu.setText("🧠 Formula Module ⬇")
        self.btn_formula_menu.setPopupMode(QToolButton.MenuButtonPopup)
        self.btn_formula_menu.setFixedSize(180, 28)

        # Tạo menu
        formula_menu = QMenu(self)
        action_build = formula_menu.addAction("📐 Build Formula")
        action_build.triggered.connect(self.open_formula_dialog)
        action_insert = formula_menu.addAction("📥 Insert Formula")
        action_insert.triggered.connect(self.insert_formula_feature)

        self.btn_formula_menu.setMenu(formula_menu)

        filter_layout.addWidget(self.btn_formula_menu)

        # 👉 Nút Export
        self.btn_export = QPushButton("💾 Export")
        self.btn_export.setFixedSize(120, 28)
        self.btn_export.clicked.connect(self.export_data)

        filter_layout.addWidget(self.btn_export)

        filter_layout.addStretch()
        # 👉 Bảng dữ liệu
        self.table = QTableView()
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.model = PandasModel(self.df_full)
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)

    def update_table(self):
        start = self.start_time.dateTime().toPython()
        end = self.end_time.dateTime().toPython()
        filtered_df = filter_dataframe_by_datetime(self.df_full, start, end)

        # Cập nhật model và table
        self.model = PandasModel(filtered_df)
        self.table.setModel(self.model)
        self.table.resizeColumnsToContents()

    def open_formula_dialog(self):
        main_window = self.parent()
        if hasattr(main_window, "parent_main_window"):
            main_window = main_window.parent_main_window

        dialog = BuildFormulaDialog(main_window)
        dialog.exec()

    def insert_formula_feature(self):
        updated_df = insert_formula_feature(self.df_full, self)
        if updated_df is not None:
            self.df_full = updated_df
            if hasattr(self.parent(), "parent_main_window"):
                self.parent().parent_main_window.set_final_df(updated_df)
            self.update_table()

    def open_cleaning_dialog(self):
        main_window = self.parent()
        if hasattr(main_window, "parent_main_window"):
            main_window = main_window.parent_main_window

        dialog = DataCleaningDialog(main_window)
        if dialog.exec():
            cleaned_df = dialog.get_cleaned_data()
            if cleaned_df is not None:
                self.df_full = cleaned_df
                if hasattr(main_window, "set_final_df"):
                    main_window.set_final_df(cleaned_df, folder_name=self.df_key)
                self.update_table()

                if hasattr(self.parent(), "parent_main_window"):
                    self.parent().parent_main_window.set_final_df(cleaned_df, folder_name=self.df_key)

        else:
            QMessageBox.warning(self, "Không khả dụng", "Không thể mở chức năng Clean Data nếu không có liên kết đến Main Window.")


    def export_data(self):
        if self.model._df.empty:
            QMessageBox.warning(self, "Cảnh báo", "Không có dữ liệu để xuất.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu dữ liệu đã lọc",
            "",
            "Excel file (*.xlsx);;CSV file (*.csv)"
        )

        if not file_path:
            return

        try:
            if file_path.endswith(".csv"):
                self.model._df.to_csv(file_path, index=False)
            elif file_path.endswith(".xlsx"):
                self.model._df.to_excel(file_path, index=False, engine='openpyxl')
            else:
                self.model._df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Thành công", f"Đã lưu dữ liệu vào:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu file:\n{str(e)}")

        
    def open_delete_columns_dialog(self):
        dialog = DeleteColumnsDialog(self)
        if dialog.exec():
            self.update_table()

    def open_nan_status_dialog(self):
        if self.df_full is None or self.df_full.empty:
            QMessageBox.warning(
                self,
                "NaN status",
                "Chưa có dữ liệu hoặc DataFrame đang trống."
            )
            return

        dialog = NaNStatusDialog(self.df_full, self)
        if dialog.exec():
            cleaned_df = dialog.get_cleaned_df()
            if cleaned_df is None:
                return

            self.df_full = cleaned_df

            main_window = self.parent()
            if hasattr(main_window, "parent_main_window"):
                main_window = main_window.parent_main_window

            if main_window is not None and hasattr(main_window, "set_final_df"):
                main_window.set_final_df(cleaned_df, folder_name=self.df_key)

            self.update_table()
