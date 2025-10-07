from PySide6.QtWidgets import QDialog, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
from PySide6.QtCore import Qt
import pandas as pd


class HeatmapDialog(QDialog):
    def __init__(self, df: pd.DataFrame, selected_vars: list[str], method="pearson", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Heatmap Correlation")
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.resize(900, 700)

        layout = QVBoxLayout(self)

        # Lọc các biến số hợp lệ
        selected_numeric = [
            col for col in selected_vars
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col])
        ]

        if not selected_numeric or len(selected_numeric) < 2:
            raise ValueError("Không đủ biến số để vẽ Heatmap")

        corr_df = df[selected_numeric].corr(method=method)

        # Tính kích thước linh hoạt theo số biến
        n_vars = len(corr_df.columns)
        cell_size = 0.7
        width = min(max(8, n_vars * cell_size), 28)
        height = min(max(6, n_vars * cell_size), 28)

        self.fig = Figure(figsize=(width, height))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        self.ax = self.fig.add_subplot(111)

        sns.heatmap(
            corr_df,
            annot=True,
            fmt=".2f",
            cmap="coolwarm",
            ax=self.ax,
            cbar=True
        )
        self.ax.set_title(f"Heatmap Correlation ({method.title()})", fontsize=14)
        self.ax.set_xticklabels(self.ax.get_xticklabels(), rotation=60, ha='right', fontsize=9)
        self.ax.set_yticklabels(self.ax.get_yticklabels(), rotation=0, fontsize=9)
        self.fig.tight_layout()
        self.canvas.draw()
