from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QDateTimeEdit, QSpinBox,
    QMessageBox, QDialog, QDialogButtonBox, QCheckBox, QScrollArea,
    QSizePolicy
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QDateTime, QUrl
import pandas as pd
import plotly.io as pio
import tempfile
from project1_main_tab.Plotly_modules.plotly_line_chart import plotly_line_chart
from project1_main_tab.Plotly_modules.plotly_scatter2d import plotly_scatter2d
from project1_main_tab.Plotly_modules.plotly_bar_max import plotly_bar_max
from project1_main_tab.Plotly_modules.plotly_histogram import plotly_histogram
from project1_main_tab.Plotly_modules.plotly_boxplot import plotly_boxplot
from project1_main_tab.Plotly_modules.plotly_violin import plotly_violin
from project1_main_tab.Plotly_modules.plotly_heatmap import plotly_heatmap
from project1_main_tab.Plotly_modules.plotly_zscore_scatter import plotly_zscore_scatter
from project1_main_tab.Plotly_modules.plotly_pairplot import plotly_pairplot
from project1_main_tab.Plotly_modules.plotly_hist_box import plotly_hist_box
from project1_main_tab.Plotly_modules.plotly_pie import plotly_pie
from project1_main_tab.Plotly_modules.plotly_area import plotly_area
from project1_main_tab.Plotly_modules.plotly_parcoords import plotly_parcoords
from project1_main_tab.Plotly_modules.plotly_spc_control_chart import plotly_spc_i_chart
from project1_main_tab.Plotly_modules.plotly_rolling_band import plotly_rolling_band
from project1_main_tab.Plotly_modules.plotly_mw_binned_scatter import plotly_mw_binned_scatter
from project1_main_tab.Plotly_modules.plotly_100_stacked_bar import plotly_100_stacked_bar
from project1_main_tab.Plotly_modules.plotly_xy_plot import plotly_xy_plot
from project1_main_tab.plot_tab import MultiRangeDialog
from project1_main_tab.plot_tab import MultiRangeDialog, SimpleScaleDialog
IGNORED_COLUMNS = {'datetime', 'date', 'time', 'sourcefolder'}


class VariableSelectorDialog(QDialog):
    def __init__(self, columns, selected_vars=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn biến để vẽ")
        self.selected_vars = selected_vars or []
        self.checkboxes = []

        layout = QVBoxLayout(self)
        self.setMinimumSize(400, 800)

        checkbox_widget = QWidget()
        checkbox_layout = QVBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(4, 4, 4, 4)
        checkbox_layout.setSpacing(2)

        for col in columns:
            cb = QCheckBox(col)
            cb.setChecked(col in self.selected_vars)
            checkbox_layout.addWidget(cb)
            self.checkboxes.append(cb)
        checkbox_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(checkbox_widget)
        scroll.setMinimumHeight(200)
        scroll.setMaximumHeight(800)

        layout.addWidget(scroll)

        action_layout = QHBoxLayout()
        btn_check_all = QPushButton("✅ Chọn tất cả")
        btn_uncheck_all = QPushButton("❌ Bỏ chọn tất cả")
        btn_check_all.clicked.connect(self.check_all)
        btn_uncheck_all.clicked.connect(self.uncheck_all)
        action_layout.addWidget(btn_check_all)
        action_layout.addWidget(btn_uncheck_all)
        layout.addLayout(action_layout)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_selected_variables(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

    def check_all(self):
        for cb in self.checkboxes:
            cb.setChecked(True)

    def uncheck_all(self):
        for cb in self.checkboxes:
            cb.setChecked(False)


class XYVariableSelectorDialog(QDialog):
    """Dialog chọn 1 biến X và nhiều biến Y cho XY Plot."""
    def __init__(self, columns: list[str], x_col: str = "", y_cols: list[str] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("XY Plot — Chọn biến")
        self.setMinimumSize(420, 560)
        y_cols = y_cols or []

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # --- X variable (single select ComboBox) ---
        layout.addWidget(QLabel("<b>Trục X (1 biến):</b>"))
        self.x_combo = QComboBox()
        self.x_combo.addItems(columns)
        if x_col in columns:
            self.x_combo.setCurrentText(x_col)
        layout.addWidget(self.x_combo)

        # --- Y variables (multi checkboxes) ---
        layout.addWidget(QLabel("<b>Trục Y (nhiều biến):</b>"))

        y_widget = QWidget()
        y_layout = QVBoxLayout(y_widget)
        y_layout.setContentsMargins(4, 4, 4, 4)
        y_layout.setSpacing(2)
        self.y_checkboxes: list[QCheckBox] = []
        for col in columns:
            cb = QCheckBox(col)
            cb.setChecked(col in y_cols)
            y_layout.addWidget(cb)
            self.y_checkboxes.append(cb)
        y_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(y_widget)
        scroll.setMinimumHeight(250)
        layout.addWidget(scroll)

        action_row = QHBoxLayout()
        btn_all = QPushButton("✅ Chọn tất cả Y")
        btn_none = QPushButton("❌ Bỏ chọn Y")
        btn_all.clicked.connect(lambda: [cb.setChecked(True) for cb in self.y_checkboxes])
        btn_none.clicked.connect(lambda: [cb.setChecked(False) for cb in self.y_checkboxes])
        action_row.addWidget(btn_all)
        action_row.addWidget(btn_none)
        layout.addLayout(action_row)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_x_col(self) -> str:
        return self.x_combo.currentText()

    def get_y_cols(self) -> list[str]:
        return [cb.text() for cb in self.y_checkboxes if cb.isChecked()]


class PlotlyTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = pd.DataFrame()
        self.selected_vars = []
        self.scales: dict[str, float] = {}
        self._last_fig = None
        self._last_html_path = None  # Đường dẫn HTML đồ thị cuối → Monitoring nhúng nguyên đồ thị (không dùng kaleido)
        self._xy_swapped = False
        self._xy_x_col: str = ""
        self._xy_y_cols: list[str] = []

        # ===== ROOT LAYOUT: full khung =====
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ===== Top controls =====
        topbar = QHBoxLayout()
        topbar.setContentsMargins(6, 6, 6, 6)  # giữ chút padding cho thanh điều khiển
        topbar.setSpacing(6)

        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems([
            "Line", "Area", "Scatter", "XY Plot", "Bar (Max)", "100% Stacked Bar", "Z-score Scatter",
            "Heatmap Correlation", "Histogram", "Boxplot",
            "Histogram + Boxplot", "Violin", "Pairplot",
            "Pie", "Parallel Coordinates","SPC Control (I-Chart)",
"Rolling Band",
"MW-binned Scatter",

        ])

        self.btn_variable = QPushButton("🧩 Variable")
        self.btn_variable.clicked.connect(self.open_variable_dialog)

        self.btn_swap = QPushButton("⇄ Swap X-Y")
        self.btn_swap.setToolTip("Đảo trục X và Y cho Scatter")
        self.btn_swap.clicked.connect(self.swap_xy)
        self.btn_swap.setVisible(False)

        self.range_spin = QSpinBox()
        self.range_spin.setMinimum(1)
        self.range_spin.setMaximum(10)
        self.range_spin.setValue(1)
        self.range_spin.setVisible(False)
        self.chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)

        self.start_time = QDateTimeEdit()
        self.end_time = QDateTimeEdit()
        for dt in [self.start_time, self.end_time]:
            dt.setDisplayFormat("yyyy-MM-dd HH:mm")
            dt.setCalendarPopup(True)
        self.btn_scale = QPushButton("⚖️ Scale")
        self.btn_scale.setToolTip("Scale từng biến (y = y * scale), giống Plot tab")
        self.btn_scale.clicked.connect(self.open_scale_dialog)
        btn_plot = QPushButton("📊 Vẽ")
        btn_plot.clicked.connect(self.draw_chart)

        topbar.addWidget(QLabel("Biểu đồ:"))
        topbar.addWidget(self.chart_type_combo)
        topbar.addWidget(self.btn_variable)
        topbar.addWidget(self.btn_swap)
        topbar.addWidget(self.btn_scale)
        topbar.addWidget(QLabel("Range:"))
        topbar.addWidget(self.range_spin)
        topbar.addWidget(QLabel("⏱ From:"))
        topbar.addWidget(self.start_time)
        topbar.addWidget(QLabel("To:"))
        topbar.addWidget(self.end_time)
        topbar.addStretch()
        topbar.addWidget(btn_plot)

        root.addLayout(topbar)
        self.window_spin = QSpinBox()
        self.window_spin.setMinimum(10)
        self.window_spin.setMaximum(5000)
        self.window_spin.setValue(60)
        self.window_spin.setToolTip("Rolling/SPC window (số điểm)")

        topbar.addWidget(QLabel("Window:"))
        topbar.addWidget(self.window_spin)
        # ===== Plot view =====
        self.plot_view = QWebEngineView()
        self.plot_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.plot_view, 1)  # stretch=1 -> ăn hết phần còn lại

        # (tuỳ chọn) zoom factor cho "đầy" hơn, anh chỉnh 1.0~1.2 theo ý
        self.plot_view.setZoomFactor(1.0)

    def update_plot(self, df: pd.DataFrame):
        self.df = df.copy()

        if "datetime" in self.df.columns and "Datetime" not in self.df.columns:
            self.df.rename(columns={"datetime": "Datetime"}, inplace=True)

        if 'Datetime' in self.df.columns:
            self.df['Datetime'] = pd.to_datetime(self.df['Datetime'])
            self.start_time.setDateTime(QDateTime(self.df['Datetime'].min()))
            self.end_time.setDateTime(QDateTime(self.df['Datetime'].max()))

        all_plot_cols = [col for col in self.df.columns if col.lower() not in IGNORED_COLUMNS]
        self.selected_vars = [col for col in self.selected_vars if col in all_plot_cols]

    def open_variable_dialog(self):
        if self.df.empty:
            QMessageBox.warning(self, "Cảnh báo", "Chưa có dữ liệu.")
            return

        columns = [col for col in self.df.columns if col.lower() not in IGNORED_COLUMNS]
        chart_type = self.chart_type_combo.currentText()

        if chart_type == "XY Plot":
            dialog = XYVariableSelectorDialog(columns, self._xy_x_col, self._xy_y_cols, self)
            if dialog.exec():
                self._xy_x_col = dialog.get_x_col()
                self._xy_y_cols = dialog.get_y_cols()
                self.draw_chart()
        else:
            dialog = VariableSelectorDialog(columns, self.selected_vars or columns, self)
            if dialog.exec():
                self.selected_vars = dialog.get_selected_variables()
                self.draw_chart()

    def _on_chart_type_changed(self, text: str):
        t = (text or "").strip().lower()
        is_line = (t == "line")
        is_bar = (t == "bar (max)")
        is_stacked = (t == "100% stacked bar")
        is_scatter = (t == "scatter")
        self.range_spin.setVisible(is_line or is_bar or is_stacked)
        self.btn_swap.setVisible(is_scatter)
        if not is_scatter:
            self._xy_swapped = False
            self.btn_swap.setText("⇄ Swap X-Y")

    def swap_xy(self):
        if len(self.selected_vars) == 2:
            self._xy_swapped = not self._xy_swapped
            label = "⇄ Swap X-Y" if self._xy_swapped else "⇄ Swap X-Y"
            self.btn_swap.setText(label)
            self.draw_chart()

    def get_filtered_df(self):
        df_filtered = self.df.copy()
        if 'Datetime' in df_filtered.columns:
            start_dt = self.start_time.dateTime().toPython()
            end_dt = self.end_time.dateTime().toPython()
            df_filtered = df_filtered[
                (df_filtered['Datetime'] >= start_dt) &
                (df_filtered['Datetime'] <= end_dt)
            ]
        return df_filtered

    def draw_chart(self):
        df_filtered = self.get_filtered_df()
        chart_type = self.chart_type_combo.currentText()

        if chart_type != "XY Plot" and not self.selected_vars:
            QMessageBox.warning(self, "Thiếu biến", "Chọn ít nhất 1 biến để vẽ.")
            return
        if df_filtered.empty:
            QMessageBox.warning(self, "Không có dữ liệu", "Không có dữ liệu trong khoảng thời gian.")
            return

        if chart_type == "XY Plot":
            if not self._xy_x_col or not self._xy_y_cols:
                QMessageBox.warning(self, "Thiếu biến", "Bấm 🧩 Variable để chọn 1 biến X và ít nhất 1 biến Y.")
                return
            try:
                fig = plotly_xy_plot(df_filtered, self._xy_x_col, self._xy_y_cols)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không vẽ được XY Plot: {e}")
                return
            if fig is None:
                QMessageBox.warning(self, "Không đủ dữ liệu", "Không có dữ liệu hợp lệ để vẽ.")
                return
            self._last_fig = fig
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            pio.write_html(fig, file=tmp.name, include_plotlyjs=True, full_html=True,
                          auto_open=False, config={"responsive": True, "displayModeBar": True})
            self._last_html_path = tmp.name
            self.plot_view.load(QUrl.fromLocalFile(tmp.name))
            return

        if chart_type == "Scatter":
            if len(self.selected_vars) != 2:
                QMessageBox.warning(self, "Thiếu biến", "Scatter cần đúng 2 biến (X và Y).")
                return
            x_var, y_var = (self.selected_vars[1], self.selected_vars[0]) if self._xy_swapped else (self.selected_vars[0], self.selected_vars[1])
            try:
                fig = plotly_scatter2d(df_filtered, x_var, y_var)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không vẽ được scatter: {e}")
                return
            if fig is None:
                QMessageBox.warning(self, "Không đủ dữ liệu", "Không đủ điểm để vẽ (cần ≥2 điểm).")
                return
            self._last_fig = fig
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            pio.write_html(fig, file=tmp.name, include_plotlyjs=True, full_html=True,
                          auto_open=False, config={"responsive": True, "displayModeBar": True})
            self._last_html_path = tmp.name
            self.plot_view.load(QUrl.fromLocalFile(tmp.name))
            return

        elif chart_type == "Line":
            x = "Datetime" if "Datetime" in df_filtered.columns else (
                self.selected_vars[0] if self.selected_vars else "x"
            )

            time_ranges = None

            # ✅ 1) check theo df_filtered (không check self.df)
            if self.range_spin.value() > 1 and "Datetime" in df_filtered.columns:

                # ✅ 2) dialog nhận df_filtered để khoảng range chỉ nằm trong cửa sổ đã lọc
                dlg = MultiRangeDialog(self.range_spin.value(), df=df_filtered, parent=self)
                if dlg.exec():
                    time_ranges = dlg.get_ranges()
                else:
                    return

            # ✅ 3) vẽ từ df_filtered (không vẽ từ self.df)
            fig = plotly_line_chart(
                df_filtered,
                x,
                self.selected_vars,
                time_ranges=time_ranges,
                scales=self.scales,   # giữ nguyên scale như anh muốn
            )

            self._last_fig = fig
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            plot_config = {
                "responsive": True,
                "displayModeBar": True,
                "scrollZoom": True,
                "displaylogo": False
            }

            pio.write_html(
                fig,
                file=tmp.name,
                include_plotlyjs=True,
                full_html=True,
                auto_open=False,
                config=plot_config
            )
            self._last_html_path = tmp.name
            self.plot_view.load(QUrl.fromLocalFile(tmp.name))
            return
        elif chart_type == "Bar (Max)":
            time_ranges = None
            if self.range_spin.value() > 1 and "Datetime" in df_filtered.columns:
                dlg = MultiRangeDialog(self.range_spin.value(), df=df_filtered, parent=self)
                if dlg.exec():
                    time_ranges = dlg.get_ranges()
                else:
                    return

            fig = plotly_bar_max(
                df_filtered,                 # ✅ dùng df_filtered
                self.selected_vars,
                title="Max value",
                time_ranges=time_ranges,     # ✅ vẫn giữ range > 1
                # scales=self.scales  # nếu bar module của anh có scales thì giữ, không có thì bỏ
            )

            self._last_fig = fig
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            plot_config = {"responsive": True, "displayModeBar": True, "scrollZoom": True, "displaylogo": False}
            pio.write_html(fig, file=tmp.name, include_plotlyjs=True, full_html=True, auto_open=False, config=plot_config)
            self._last_html_path = tmp.name
            self.plot_view.load(QUrl.fromLocalFile(tmp.name))
            return
        elif chart_type == "Area":
            if "Datetime" in df_filtered.columns:
                x = "Datetime"
                y_cols = [c for c in self.selected_vars if c in df_filtered.columns and c != "Datetime" and pd.api.types.is_numeric_dtype(df_filtered[c])]
            else:
                x = self.selected_vars[0] if self.selected_vars else None
                y_cols = [c for c in self.selected_vars[1:] if c in df_filtered.columns] if len(self.selected_vars) > 1 else self.selected_vars
            if not y_cols:
                y_cols = [c for c in self.selected_vars if c in df_filtered.columns and c != x]
            if not x or not y_cols:
                QMessageBox.warning(self, "Thiếu biến", "Area cần cột Datetime và ít nhất 1 biến numeric.")
                return
            fig = plotly_area(df_filtered, x, y_cols)
            if fig is not None:
                self._last_fig = fig
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
                pio.write_html(fig, file=tmp.name, include_plotlyjs=True, full_html=True,
                              auto_open=False, config={"responsive": True, "displayModeBar": True})
                self._last_html_path = tmp.name
                self.plot_view.load(QUrl.fromLocalFile(tmp.name))
            return

        # Các loại biểu đồ mới (tương tự Plot tab)
        plot_config = {
            "responsive": True,
            "displayModeBar": True,
            "scrollZoom": True,
            "displaylogo": False,
        }
        fig = None
        try:
            if chart_type == "Histogram":
                fig = plotly_histogram(df_filtered, self.selected_vars)
            elif chart_type == "Boxplot":
                fig = plotly_boxplot(df_filtered, self.selected_vars)
            elif chart_type == "Violin":
                fig = plotly_violin(df_filtered, self.selected_vars)

            elif chart_type == "Histogram + Boxplot":
                fig = plotly_hist_box(df_filtered, self.selected_vars)
            elif chart_type == "Heatmap Correlation":
                if len(self.selected_vars) < 2:
                    QMessageBox.warning(self, "Thiếu biến", "Heatmap cần ít nhất 2 biến.")
                    return
                fig = plotly_heatmap(df_filtered, self.selected_vars)
            elif chart_type == "Z-score Scatter":
                if len(self.selected_vars) != 2:
                    QMessageBox.warning(self, "Thiếu biến", "Z-score Scatter cần đúng 2 biến.")
                    return
                fig = plotly_zscore_scatter(df_filtered, self.selected_vars[0], self.selected_vars[1])
            elif chart_type == "Pairplot":
                if len(self.selected_vars) < 2:
                    QMessageBox.warning(self, "Thiếu biến", "Pairplot cần ít nhất 2 biến.")
                    return
                fig = plotly_pairplot(df_filtered, self.selected_vars)
            elif chart_type == "Pie":
                fig = plotly_pie(df_filtered, self.selected_vars)
            elif chart_type == "SPC Control (I-Chart)":
                if "Datetime" not in df_filtered.columns:
                    QMessageBox.warning(self, "Thiếu Datetime", "SPC cần cột Datetime.")
                    return
                selected_tag = self.selected_vars[0]
                window = int(self.window_spin.value())
                fig = plotly_spc_i_chart(
                    df=df_filtered,
                    x_col="Datetime",
                    y_col=selected_tag,
                    window=window,
                    sigma=3.0
                )

            elif chart_type == "Rolling Band":
                if "Datetime" not in df_filtered.columns:
                    QMessageBox.warning(self, "Thiếu Datetime", "Rolling Band cần cột Datetime.")
                    return
                selected_tag = self.selected_vars[0]
                window = int(self.window_spin.value())
                fig = plotly_rolling_band(
                    df=df_filtered,
                    x_col="Datetime",
                    y_col=selected_tag,
                    window=window,
                    band_sigma=1.0
                )

            elif chart_type == "MW-binned Scatter":
                if "Datetime" not in df_filtered.columns:
                    QMessageBox.warning(self, "Thiếu Datetime", "MW-binned Scatter cần cột Datetime.")
                    return
                if "NET MW" not in df_filtered.columns:
                    QMessageBox.warning(self, "Thiếu NET MW", "Cần cột 'NET MW' để chia bin theo tải.")
                    return
                selected_tag = self.selected_vars[0]
                fig = plotly_mw_binned_scatter(
                    df=df_filtered,
                    x_col="Datetime",
                    y_col=selected_tag,
                    mw_col="NET MW",
                    bin_size=50.0,
                    max_bins=8
                )

            elif chart_type == "Parallel Coordinates":
                if len(self.selected_vars) < 2:
                    QMessageBox.warning(self, "Thiếu biến", "Parallel Coordinates cần ít nhất 2 biến numeric.")
                    return
                fig = plotly_parcoords(df_filtered, self.selected_vars)
            elif chart_type == "100% Stacked Bar":
                time_ranges = None
                if self.range_spin.value() > 1 and "Datetime" in self.df.columns:
                    dlg = MultiRangeDialog(self.range_spin.value(), df=self.df, parent=self)
                    if dlg.exec():
                        time_ranges = dlg.get_ranges()
                    else:
                        return

                # case anh nói: chỉ chọn 4 feature -> lấy hết làm value_cols
                value_cols = list(self.selected_vars)

                fig = plotly_100_stacked_bar(
                    df=self.df,                 # dùng df gốc để multi-range chính xác giống Line
                    value_cols=value_cols,
                    group_col=None,             # 1 cột cho mỗi range (Range 1, Range 2...)
                    title="100% Stacked Bar (by Range)",
                    decimals=2,
                    show_percent_text=True,
                    agg="mean",
                    time_ranges=time_ranges,    # <<< quan trọng
                )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không vẽ được: {e}")
            return

        if fig is not None:
            self._last_fig = fig
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            pio.write_html(fig, file=tmp.name, include_plotlyjs=True, full_html=True,
                          auto_open=False, config=plot_config)
            self._last_html_path = tmp.name
            self.plot_view.load(QUrl.fromLocalFile(tmp.name))
        elif chart_type in ["Histogram", "Boxplot", "Bar (Max)", "Violin", "Histogram + Boxplot",
                    "Heatmap Correlation", "Z-score Scatter", "100% Stacked Bar", "Pairplot",
                    "Pie", "Parallel Coordinates",
                    "SPC Control (I-Chart)", "Rolling Band", "MW-binned Scatter", "Deviation Baseline"]:
            QMessageBox.warning(self, "Không hỗ trợ", f"Chưa hỗ trợ chart type: {chart_type}")

    def get_last_html_path(self) -> str | None:
        """Đường dẫn file HTML đồ thị cuối — Monitoring load trực tiếp (giống tab Plotly)."""
        return self._last_html_path or None

    def get_last_html_content(self) -> str | None:
        """Nội dung HTML đồ thị cuối — dùng khi lưu config hoặc khi không dùng path."""
        if not self._last_html_path:
            return None
        try:
            with open(self._last_html_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
    def get_current_plotly_spec(self) -> dict:
        return {
            "chart_type": self.chart_type_combo.currentText(),
            "selected_vars": list(self.selected_vars),
            "range_spin": int(self.range_spin.value()),
        }
    def open_scale_dialog(self):
        if not self.selected_vars:
            QMessageBox.warning(self, "Thiếu biến", "Chọn biến trước rồi hãy scale.")
            return
        dlg = SimpleScaleDialog(self.selected_vars, self.scales, self)
        if dlg.exec():
            self.scales = dlg.get_scales()
            self.draw_chart()