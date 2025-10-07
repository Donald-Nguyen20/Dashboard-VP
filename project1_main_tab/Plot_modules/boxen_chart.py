import seaborn as sns
import pandas as pd
import numpy as np
import mplcursors
from PySide6.QtWidgets import QMessageBox

def plot_boxenplot_chart(plot_tab, df):
    selected = plot_tab.selected_vars
    if not selected:
        QMessageBox.warning(plot_tab, "Warning", "Hãy chọn ít nhất 1 biến để vẽ boxenplot.")
        return

    num_vars = len(selected)
    ncols = 2
    nrows = int(np.ceil(num_vars / ncols))

    plot_tab.figure.clear()
    axes = plot_tab.figure.subplots(nrows, ncols, squeeze=False)

    has_datetime = 'Datetime' in df.columns

    for idx, col in enumerate(selected):
        row, col_pos = divmod(idx, ncols)
        ax = axes[row][col_pos]

        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            sns.boxenplot(y=df[col], ax=ax, k_depth='trustworthy')
            ax.set_title(f'Boxenplot: {col}')

            # Vẽ điểm tàng hình để attach tooltip
            points = sns.stripplot(y=df[col], ax=ax, color='black', alpha=0.0, jitter=False)

            y_values = df[col].tolist()
            outlier_indices = list(df.index)
            datetimes = df['Datetime'].tolist() if has_datetime else ["N/A"] * len(df)

            cursor = mplcursors.cursor(points.collections[0], hover=True)

            def make_on_add(colname, y_values, outlier_indices, datetimes):
                def on_add(sel):
                    yval = sel.target[1]
                    idx = (np.abs(np.array(y_values) - yval)).argmin()
                    index_goc = outlier_indices[idx]
                    datetime_str = datetimes[idx]
                    msg = f"{colname}\nValue: {yval:.2f}\nIndex: {index_goc}\nDatetime: {datetime_str}"
                    sel.annotation.set_text(msg)
                    sel.annotation.get_bbox_patch().set(fc="white", alpha=0.95)
                return on_add

            cursor.connect("add", make_on_add(col, y_values, outlier_indices, datetimes))

        else:
            ax.set_visible(False)

    plot_tab.figure.tight_layout()
    plot_tab.canvas.draw()
