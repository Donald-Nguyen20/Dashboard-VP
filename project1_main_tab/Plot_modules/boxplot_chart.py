import numpy as np
import pandas as pd
from PySide6.QtWidgets import QMessageBox
import mplcursors

def get_datetime_col(df):
    for c in df.columns:
        if c.lower() == "datetime":
            return c
    for c in df.columns:
        if "date" in c.lower() or "time" in c.lower():
            return c
    return None

def plot_boxplot_chart(plot_tab, df):
    selected = plot_tab.selected_vars
    if not selected:
        QMessageBox.warning(plot_tab, "Warning", "Hãy chọn ít nhất 1 biến để vẽ boxplot.")
        return

    datetime_col = get_datetime_col(df)

    num_vars = len(selected)
    ncols = 2 if num_vars > 1 else 1
    nrows = int(np.ceil(num_vars / ncols))

    plot_tab.figure.clear()
    axes = plot_tab.figure.subplots(nrows, ncols, squeeze=False)
    all_scatters = []

    for idx, col in enumerate(selected):
        row, col_pos = divmod(idx, ncols)
        ax = axes[row][col_pos]
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            col_data = df[col].dropna()
            col_data_for_match = col_data.copy()
            used_indices = set()
            bp = ax.boxplot(
                col_data, vert=True, patch_artist=True,
                boxprops=dict(facecolor='#afd8ff', color='#0d3054'),
                medianprops=dict(color='#ff4e00', linewidth=2),
                flierprops=dict(marker='o', markerfacecolor='red', markersize=6, linestyle='none')
            )
            ax.set_title(col)
            ax.set_xlabel("Feature")
            ax.set_ylabel("Value")
            for flier in bp["fliers"]:
                y_outliers = flier.get_ydata()
                x_flier = flier.get_xdata()
                idx_list = []
                datetime_list = []
                for yval in y_outliers:
                    match_indices = col_data_for_match[np.isclose(col_data_for_match.values, yval)].index
                    match_index = None
                    for idx_candidate in match_indices:
                        if idx_candidate not in used_indices:
                            match_index = idx_candidate
                            break
                    if match_index is not None:
                        used_indices.add(match_index)
                        idx_list.append(match_index)
                        if datetime_col and datetime_col in df.columns:
                            dt_val = df.loc[match_index, datetime_col]
                            if pd.isna(dt_val):
                                datetime_list.append("N/A")
                            else:
                                datetime_list.append(str(dt_val))
                        else:
                            datetime_list.append("N/A")
                    else:
                        idx_list.append(None)
                        datetime_list.append("N/A")
                if len(y_outliers) > 0 and len(x_flier) > 0:
                    sc = ax.scatter([x_flier[0]]*len(y_outliers), y_outliers, alpha=0.01)
                    all_scatters.append((sc, col, y_outliers, idx_list, datetime_list))
        else:
            ax.set_visible(False)

    plot_tab.figure.tight_layout()
    plot_tab.canvas.draw()
    plot_tab.ax = axes[0][0]

    # Tooltip cho outlier scatter
    for sc, col, y_outliers, idx_list, datetime_list in all_scatters:
        cursor = mplcursors.cursor(sc, hover=True)
        def make_on_add(col, y_outliers, idx_list, datetime_list):
            def on_add(sel):
                yval = sel.target[1]
                idx = (np.abs(np.array(y_outliers) - yval)).argmin()
                index_goc = idx_list[idx]
                datetime_str = datetime_list[idx]
                msg = f"{col}\nOutlier: {yval:.2f}\nIndex: {index_goc}\nDatetime: {datetime_str}"
                sel.annotation.set_text(msg)
                sel.annotation.get_bbox_patch().set(fc="white", alpha=0.95)
            return on_add
        cursor.connect("add", make_on_add(col, y_outliers, idx_list, datetime_list))
