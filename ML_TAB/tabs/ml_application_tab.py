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
from ML_TAB.widgets.step_card import StepCard
from ML_TAB.Steps.Step7.Load_and_Deployment import predict_from_model


class MLApplicationTab(QWidget):
    """
    Tab ML: bố trí các StepCard theo hàng ngang với QScrollArea (scroll ngang).
    Màu sắc & style lấy từ QSS (ThemeManager), không set inline ở đây.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("MLApplicationTab")

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
        vp.setAttribute(Qt.WA_StyledBackground, True)  # Quan trọng để nền QSS có hiệu lực

        # HBox chứa các StepCard
        self.h = QHBoxLayout(container)
        self.h.setContentsMargins(16, 4, 16, 16)
        self.h.setSpacing(16)

        self._add_step_cards()
        self.h.addStretch(1)  # đẩy cụm card sát trái

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
            # Lưu ý: StepCard phải có objectName="StepCard" ở lớp widget (đã sửa ở widgets/step_card.py)
            # Nếu StepCard không nhận tham số role, ta gán property trực tiếp:
            card = StepCard(cfg["step"], cfg["title"], cfg["sub"], parent=self)
            card.setProperty("variant", cfg["role"])   # step1..step7 cho QSS bắt màu
            card.setFixedSize(CARD_W, CARD_H)

            # Căn top để các card thẳng hàng
            self.h.addWidget(card, 0, Qt.AlignTop)

            card.clicked.connect(self._on_step_clicked)
            self.cards.append(card)

    def _on_step_clicked(self, step_no: int):
        if step_no != 7:
            print(f"[UI] Step {step_no} clicked")
            return
        try:
            # Chọn file model
            models_dir = os.path.abspath("models")
            model_path, _ = QFileDialog.getOpenFileName(
                self, "Chọn file model", models_dir,
                "Model files (*.pkl *.sav);;All files (*.*)"
            )
            if not model_path:
                return

            # Chọn dữ liệu CSV
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