# tabs/ml_application_tab.py
from __future__ import annotations
from typing import Optional
import os, traceback
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QHBoxLayout,
    QFileDialog, QMessageBox, QFrame
)
import pandas as pd
from ML_TAB.widgets.step_card import StepCard
from ML_TAB.Steps.Step7.Load_and_Deployment import predict_from_model
from ML_TAB.Steps.Step1.data_collection import load_rawdata
# from ML_TAB.Steps.Step2.profile_report import generate_profile_json
from PySide6.QtWidgets import QLabel, QDoubleSpinBox, QPushButton
from ML_TAB.Steps.Step3.outlier_tools import (
    detect_outliers_iqr,
    detect_outliers_zscore,
    detect_outliers_modified_zscore,
    detect_outliers_isoforest,
    detect_outliers_lof,
    combine_outlier_results,
)
from ML_TAB.Steps.Step4.line_visualization_dialog import DataLinePlotDialog
from ML_TAB.Steps.Step3.outlier_dialog import OutlierResultsDialog
from PySide6.QtWidgets import QDialog, QMessageBox, QComboBox
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from ML_TAB.Steps.Step3.split_data_dialog import SplitDataDialog
from ML_TAB.Steps.Step5.regression_algorithms_dialog import RegressionAlgorithmsDialog
from ML_TAB.Steps.Step6.model_compare_dialog import ModelCompareDialog


class MLApplicationTab(QWidget):
    """
    Tab ML: bố trí các StepCard theo hàng ngang với QScrollArea (scroll ngang).
    Màu sắc & style lấy từ QSS (ThemeManager), không set inline ở đây.
    """
    def __init__(self, parent: Optional[QWidget] = None, df_provider=None):
        super().__init__(parent)
        self.setObjectName("MLApplicationTab")
        # callback để lấy DataFrame từ bên ngoài (MainWindow / Tab1)
        self.df_provider = df_provider
        # Root + Scroll
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setObjectName("mlScroll")
        scroll.setFrameShape(QFrame.NoFrame) 
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        root.addWidget(scroll)

        # Container bên trong Scroll (viewport sẽ được QSS tô nền)
        container = QWidget()
        container.setObjectName("mlContainer")
        scroll.setWidget(container)
        # 👇 cấu hình viewport (chỉ cần 1 lần setObjectName)
        vp = scroll.viewport()
        vp.setObjectName("mlViewport")
        vp.setAttribute(Qt.WA_StyledBackground, True)

        self.Rawdata = None
        self.raw_df = None
        self.cleaned_df = None


        # HBox chứa các StepCard
        self.h = QHBoxLayout(container)
        self.h.setContentsMargins(16, 4, 16, 16)
        self.h.setSpacing(16)

        self._add_step_cards()
        self.h.addStretch(1)

        # Font chung nhẹ nhàng (màu/viền do QSS quyết định)
        base_font = QFont()
        base_font.setPointSize(10)
        self.setFont(base_font)

    def _add_step_cards(self):
        steps = [
            dict(step=1, title="Data collection",    sub="", role="step1"),
            dict(step=2, title="Statistics",         sub="", role="step2"),
            dict(step=3, title="Data preprocessing", sub="", role="step3"),
            dict(step=4, title="Data visualization", sub="", role="step4"),
            dict(step=5, title="Model building",     sub="", role="step5"),
            dict(step=6, title="Model evaluation",   sub="", role="step6"),
            dict(step=7, title="Model deployment",   sub="", role="step7"),
        ]
        CARD_W, CARD_H = 220, 110
        self.cards: list[StepCard] = []

        for cfg in steps:
            card = StepCard(cfg["step"], cfg["title"], cfg["sub"], parent=self)
            card.setProperty("variant", cfg["role"])
            card.setFixedSize(CARD_W, CARD_H)

            if cfg["step"] == 3:
                # === CỘT STEP 3: card ở trên, NÚT CON ở dưới (cùng size) ===
                box = QFrame(self)
                vlay = QVBoxLayout(box)
                vlay.setContentsMargins(0, 0, 0, 0)
                vlay.setSpacing(10)

                # 3.1) Step 3 card (giữ như cũ)
                vlay.addWidget(card, 0, Qt.AlignTop)

                # 3.2) Nút con "Detect Outlier"
                btn = QPushButton("Detect Outlier", box)
                btn.setObjectName("btnDetectOutlier")
                btn.setFixedSize(CARD_W, CARD_H)
                vlay.addWidget(btn, 0, Qt.AlignTop)
                btn.clicked.connect(self._on_detect_outlier)
                # 3.3) Nút con "Split data"
                btn_split = QPushButton("Split data", box)
                btn_split.setObjectName("btnSplitData")
                btn_split.setFixedSize(CARD_W, CARD_H)
                vlay.addWidget(btn_split, 0, Qt.AlignTop)
                btn_split.clicked.connect(self._on_split_data)

                self.btnSplitData = btn_split

                # Đưa CỘT Step 3 (card + nút con) vào hàng ngang self.h
                self.h.addWidget(box, 0, Qt.AlignTop)

                # Giữ hành vi click của Step 3 card như cũ
                card.clicked.connect(self._on_step_clicked)

                # (tuỳ chọn) lưu tham chiếu nếu cần dùng sau
                self.btnDetectOutlier = btn

            elif cfg["step"] == 5:
                # === CỘT STEP 5: card ở trên, 2 NÚT CON ở dưới ===
                box = QFrame(self)
                vlay = QVBoxLayout(box)
                vlay.setContentsMargins(0, 0, 0, 0)
                vlay.setSpacing(10)

                # 5.1) Step 5 card (Model building)
                vlay.addWidget(card, 0, Qt.AlignTop)

                # 5.2) Nút Regression
                btn_reg = QPushButton("Regression", box)
                btn_reg.setObjectName("btnRegression")
                btn_reg.setFixedSize(CARD_W, CARD_H)
                
                vlay.addWidget(btn_reg, 0, Qt.AlignTop)
                btn_reg.clicked.connect(self._on_regression_clicked)

                # 5.3) Nút Classification
                btn_clf = QPushButton("Classification", box)
                btn_clf.setObjectName("btnClassification")
                btn_clf.setFixedSize(CARD_W, CARD_H)
                vlay.addWidget(btn_clf, 0, Qt.AlignTop)
                btn_clf.clicked.connect(self._on_classification_clicked)

                # Đưa CỘT Step 5 (card + 2 nút con) vào HBox
                self.h.addWidget(box, 0, Qt.AlignTop)

                # Card Step 5 vẫn click được như cũ (nếu sau này dùng)
                card.clicked.connect(self._on_step_clicked)

                # Lưu tham chiếu nếu cần
                self.btnRegression = btn_reg
                self.btnClassification = btn_clf

            else:
                # Các step khác giữ nguyên: chỉ có card
                self.h.addWidget(card, 0, Qt.AlignTop)
                card.clicked.connect(self._on_step_clicked)

            self.cards.append(card)



    def _on_step_clicked(self, step_no: int):
        # === STEP 1: Data collection ===
        if step_no == 1:
            try:
                df = None

                # 1) Thử lấy từ Tab 1 nếu có df_provider
                if self.df_provider is not None:
                    df = self.df_provider()
                    if df is not None and not df.empty:
                        # ✅ Lấy được dữ liệu từ Tab 1
                        self.Rawdata   = df.copy()
                        self.raw_df    = df.copy()
                        self.cleaned_df = df.copy()

                        head_info = df.head(5).to_string(index=False)
                        QMessageBox.information(
                            self,
                            "Đã lấy dữ liệu từ Tab 1",
                            f"Shape: {df.shape}\n\n"
                            f"Preview 5 dòng đầu:\n{head_info}"
                        )
                        return
                    else:
                        # Tab 1 chưa có dữ liệu → báo nhẹ rồi Fallback sang chọn file
                        QMessageBox.information(
                            self,
                            "Chưa có dữ liệu từ Tab 1",
                            "Tab 1 hiện chưa có final_df.\n"
                            "Anh có thể chọn file CSV/Excel thủ công."
                        )

                # 2) Nếu df vẫn None hoặc rỗng → cho phép chọn file
                path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Chọn file dữ liệu (CSV/Excel)",
                    os.path.abspath("."),
                    "CSV/Excel Files (*.csv *.xlsx *.xls)"
                )
                if not path:
                    return

                df = load_rawdata(path)
                self.Rawdata    = df
                self.raw_df     = df.copy()
                self.cleaned_df = df.copy()

                head_info = df.head(5).to_string(index=False)
                QMessageBox.information(
                    self, "Đã nạp dữ liệu",
                    f"File: {os.path.basename(path)}\n"
                    f"Shape: {df.shape}\n\n"
                    f"Preview 5 dòng đầu:\n{head_info}"
                )

            except Exception as e:
                QMessageBox.critical(self, "Lỗi nạp dữ liệu", str(e))
            return


        # # --- STEP 2: Statistics / Profiling (HTML full fidelity) ---
        # if step_no == 2:
        #     if getattr(self, "Rawdata", None) is None:
        #         QMessageBox.warning(self, "Chưa có dữ liệu", "Hãy chạy Step 1 để nạp Rawdata trước.")
        #         return
        #     try:
        #         json_path, html_path = generate_profile_json(
        #             self.Rawdata,
        #             out_dir="reports",
        #             html=True,
        #             minimal=True
        #         )
        #     except Exception as e:
        #         QMessageBox.critical(self, "Lỗi Step 2", str(e))
        #     return
        # --- STEP 4: Data visualization (Line) ---
        # --- STEP 2: Statistics (lightweight, no ydata_profiling) ---
        if step_no == 2:
            if getattr(self, "Rawdata", None) is None:
                QMessageBox.warning(self, "Chưa có dữ liệu", "Hãy chạy Step 1 để nạp Rawdata trước.")
                return

            df = self.Rawdata.copy()

            # thống kê nhanh cho vận hành viên (nhẹ, không cần lib ngoài)
            rows, cols = df.shape
            miss_pct = (df.isna().sum() / max(rows, 1) * 100).sort_values(ascending=False)
            miss_top = miss_pct[miss_pct > 0].head(10)

            num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            summary = df[num_cols].describe().T if num_cols else pd.DataFrame()

            msg = [
                f"Shape: {rows} rows x {cols} cols",
                f"Numeric cols: {len(num_cols)}",
                "",
                "Missing top (<=10):",
                miss_top.to_string() if not miss_top.empty else "(No missing values)",
                "",
                "Describe (numeric):",
                summary.head(10).to_string() if not summary.empty else "(No numeric columns)",
            ]

            QMessageBox.information(self, "Statistics (Step 2)", "\n".join(msg))
            return
        if step_no == 4:
            self._show_line_visualization()
            return
        # --- STEP 6: Model evaluation / comparison ---
        if step_no == 6:
            dlg = ModelCompareDialog(parent_tab=self, parent=self)
            dlg.exec()
            return
        # === CÁC STEP KHÁC (mặc định như cũ) ===
        if step_no != 7:
            print(f"[UI] Step {step_no} clicked")
            return

        # === STEP 7: Model deployment (giữ nguyên của anh) ===
        try:
            models_dir = os.path.abspath("models")
            model_path, _ = QFileDialog.getOpenFileName(
                self, "Chọn file model", models_dir,
                "Model files (*.pkl *.sav);;All files (*.*)"
            )
            if not model_path:
                return

            data_dir = os.path.abspath(".")
            data_path, _ = QFileDialog.getOpenFileName(
                self, "Chọn file dữ liệu (.csv)", data_dir,
                "CSV (*.csv);;All files (*.*)"
            )
            if not data_path:
                return

            out_path, nrows = predict_from_model(model_path, data_path)
            QMessageBox.information(
                self, "Hoàn tất",
                f"✅ Dự đoán xong {nrows} dòng.\n💾 Lưu tại: {out_path}"
            )
        except Exception:
            QMessageBox.critical(self, "Lỗi", traceback.format_exc())

    def _on_detect_outlier(self):
        # 1) Kiểm tra dữ liệu
        if self.raw_df is None and self.Rawdata is None:
            QMessageBox.warning(self, "Chưa có dữ liệu", "Hãy chạy Step 1 để nạp dữ liệu trước.")
            return

        # Ưu tiên raw_df nếu có, fallback sang Rawdata
        raw_df = self.raw_df if self.raw_df is not None else self.Rawdata

        # Nếu chưa có cleaned_df thì khởi tạo từ raw_df
        if self.cleaned_df is None:
            self.cleaned_df = raw_df.copy()

        # 👉 Luôn detect trên cleaned_df hiện tại
        df = self.cleaned_df

        try:
            # 2) Tính outlier trên df
            iqr_df   = detect_outliers_iqr(df, factor=1.5)
            zs_df    = detect_outliers_zscore(df, z=3.0)
            modz_df  = detect_outliers_modified_zscore(df, threshold=3.5)

            iso_df   = detect_outliers_isoforest(df, contamination=0.05)
            lof_df   = detect_outliers_lof(df, n_neighbors=20, contamination=0.05)



            df_inter = combine_outlier_results(iqr_df, zs_df, how="intersection")
            if df_inter is not None and not df_inter.empty:
                df_inter = df_inter.copy()
                df_inter["method"] = "IQR + Z-Score"

            # 3) Hiển thị dialog
            dlg = OutlierResultsDialog(self)
            dlg.add_tab("IQR + Z-Score", df_inter)
            dlg.add_tab("IQR", iqr_df)
            dlg.add_tab("Z-score", zs_df)
            dlg.add_tab("Modified Z-score", modz_df)
            dlg.add_tab("IsolationForest", iso_df)
            dlg.add_tab("LOF", lof_df)


            result = dlg.exec()

            # 4) Chỉ khi bấm Delete mới ghi đè Cleaned
            if result == QDialog.Accepted and getattr(dlg, "rows_to_delete", []):
                rows_to_delete = dlg.rows_to_delete

                # Xóa trên chính cleaned_df hiện tại
                cleaned = self.cleaned_df.drop(index=rows_to_delete, errors="ignore").copy()

                self.cleaned_df = cleaned

                QMessageBox.information(
                    self,
                    "Cleaning applied",
                    f"Đã xoá {len(rows_to_delete)} dòng outlier.\n"
                    f'DataFrame cleaned_df đã được cập nhật cho các bước tiếp theo.'
                )

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Detect Outlier", str(e))

    def _get_active_df_for_split(self):
        df = getattr(self, "cleaned_df", None)
        if df is not None and not df.empty:
            return df

        for name in ("raw_df", "df", "current_df", "Rawdata"):
            cand = getattr(self, name, None)
            if cand is not None and hasattr(cand, "empty") and not cand.empty:
                return cand
        return None

    def _get_numeric_cols(self, df: pd.DataFrame):
        return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    def build_xy_for_target(self, y_col: str):
        """
        Dùng train_idx/test_idx đã split ở Step 3.
        Với target y_col, X = tất cả numeric cols còn lại.
        """
        df = self._get_active_df_for_split()
        if df is None or df.empty:
            raise ValueError("No active DataFrame")

        if not hasattr(self, "train_idx") or not hasattr(self, "test_idx"):
            raise ValueError("Bạn chưa Split data ở Step 3")

        numeric_cols = self._get_numeric_cols(df)
        if y_col not in numeric_cols:
            raise ValueError(f"Target '{y_col}' phải là cột numeric")

        x_cols = [c for c in numeric_cols if c != y_col]
        if len(x_cols) == 0:
            raise ValueError("Không còn biến nào làm X")

        # lấy đúng rows theo split
        train = df.loc[self.train_idx, x_cols + [y_col]].copy()
        test = df.loc[self.test_idx, x_cols + [y_col]].copy()

        # drop NaN đồng bộ để X/y khớp dòng
        train = train.dropna(subset=x_cols + [y_col])
        test = test.dropna(subset=x_cols + [y_col])

        X_train = train[x_cols].values
        y_train = train[y_col].values
        X_test = test[x_cols].values
        y_test = test[y_col].values

        return x_cols, X_train, y_train, X_test, y_test


    def _on_split_data(self):
            df = self._get_active_df_for_split()
            if df is None or df.empty:
                QMessageBox.warning(self, "No data", "Chưa có DataFrame để split. Hãy load/clean trước.")
                return

            dlg = SplitDataDialog(df=df, parent=self)

            if dlg.exec() == QDialog.Accepted and getattr(dlg, "result", None) is not None:
                r = dlg.result

                # ✅ Lưu index split để Step 5 dùng lại (không cần split lại)
                self.train_idx = r.train_idx
                self.test_idx = r.test_idx
                self.split_test_size = r.test_size
                self.split_seed = r.random_state

                # (tuỳ chọn) Lưu luôn df train/test để xem nhanh
                self.train_df = df.loc[self.train_idx].copy()
                self.test_df = df.loc[self.test_idx].copy()

                QMessageBox.information(
                    self, "Done",
                    f"Split xong!\nTrain: {len(self.train_idx)} | Test: {len(self.test_idx)}\n"
                    f"Source: {'cleaned_df' if (self.cleaned_df is not None and not self.cleaned_df.empty) else 'raw_df/Rawdata'}"
                )



    def _on_regression_clicked(self):
        if self.cleaned_df is None and self.Rawdata is None and self.raw_df is None:
            QMessageBox.warning(self, "Chưa có dữ liệu", "Hãy chạy Step 1 trước.")
            return

        # yêu cầu đã split để train (đúng pipeline)
        if not hasattr(self, "train_idx") or not hasattr(self, "test_idx"):
            QMessageBox.warning(self, "Chưa Split", "Hãy bấm Split data ở Step 3 trước khi Regression.")
            return

        dlg = RegressionAlgorithmsDialog(parent_tab=self, parent=self)
        dlg.exec()


    def _on_classification_clicked(self):
        """
        Handler cho nút Classification dưới Step 5.
        Tạm thời chỉ hiện thông báo để test UI.
        Sau này sẽ gọi dialog / pipeline Classification ở đây.
        """
        if self.cleaned_df is None:
            QMessageBox.warning(
                self,
                "Chưa có dữ liệu",
                "Hãy chạy Step 1 (và xử lý outlier ở Step 3 nếu cần) trước khi build Classification model."
            )
            return

        print("[UI] Step 5 - Classification clicked")
        QMessageBox.information(
            self,
            "Classification",
            "Classification button clicked (Step 5). Logic training sẽ được thêm sau."
        )

    def _show_line_visualization(self):
        # Chọn nguồn dữ liệu: ưu tiên raw_df / cleaned_df
        if self.raw_df is None and self.cleaned_df is None:
            QMessageBox.warning(self, "Chưa có dữ liệu", "Hãy chạy Step 1 để nạp dữ liệu trước.")
            return

        dlg = DataLinePlotDialog(self.raw_df, self.cleaned_df, parent=self)
        dlg.exec()
