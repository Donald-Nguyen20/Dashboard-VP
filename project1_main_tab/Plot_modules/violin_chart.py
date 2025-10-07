import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mplcursors

def get_datetime_col(df):
    """
    Tìm tên cột thời gian trong DataFrame, ưu tiên 'datetime'/'Datetime', 
    nếu không sẽ tìm các cột chứa 'date' hoặc 'time'
    """
    for c in df.columns:
        if c.lower() == "datetime":
            return c
    for c in df.columns:
        if "date" in c.lower() or "time" in c.lower():
            return c
    return None

def plot_violin_chart(plot_tab, df):
    selected = plot_tab.selected_vars
    if not selected:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(plot_tab, "Cảnh báo", "Hãy chọn ít nhất 1 biến để vẽ violin plot.")
        return

    datetime_col = get_datetime_col(df)

    num_vars = len(selected)
    ncols = 2 if num_vars > 1 else 1
    nrows = int(np.ceil(num_vars / ncols))

    fig = plot_tab.figure
    fig.clear()
    axes = fig.subplots(nrows, ncols, squeeze=False)
    all_scatters = []

    for idx, col in enumerate(selected):
        row, col_pos = divmod(idx, ncols)
        ax = axes[row][col_pos]
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            # Không dùng .values ở đây!
            col_data = df[col].dropna()
            # Violin
            ax.violinplot([col_data], showmeans=True, showmedians=True, widths=0.7)
            ax.set_title(col)
            ax.set_ylabel("Giá trị")
            ax.set_xticks([])
            ax.grid(True, axis='y', linestyle='--', alpha=0.5)

            # Xác định outlier theo IQR
            Q1 = col_data.quantile(0.25)
            Q3 = col_data.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outlier_mask = (col_data < lower) | (col_data > upper)

            y_outliers = col_data[outlier_mask].values
            outlier_indices = col_data[outlier_mask].index.to_list()  # Giữ index gốc

            # Lấy datetime dựa theo index này
            if datetime_col and datetime_col in df.columns:
                datetimes = []
                for idx_val in outlier_indices:
                    try:
                        dt_val = df.loc[idx_val, datetime_col]
                        if pd.isna(dt_val):
                            datetimes.append("N/A")
                        else:
                            datetimes.append(str(dt_val))
                    except Exception:
                        datetimes.append("N/A")
            else:
                datetimes = ["N/A"] * len(y_outliers)

            sc = ax.scatter([1]*len(y_outliers), y_outliers, color='red', s=60, alpha=0.8)
            all_scatters.append((sc, col, y_outliers, outlier_indices, datetimes))
        else:
            ax.set_visible(False)

    fig.tight_layout()
    plot_tab.canvas.draw()
    plot_tab.ax = axes[0][0]

    # Tooltip cho outlier
    for sc, col, y_outliers, outlier_indices, datetimes in all_scatters:
        cursor = mplcursors.cursor(sc, hover=True)
        def make_on_add(col, y_outliers, outlier_indices, datetimes):
            def on_add(sel):
                yval = sel.target[1]
                idx = (np.abs(np.array(y_outliers) - yval)).argmin()
                index_goc = outlier_indices[idx]
                datetime_str = datetimes[idx]
                msg = f"{col}\nOutlier: {yval:.2f}\nIndex: {index_goc}\nDatetime: {datetime_str}"
                sel.annotation.set_text(msg)
                sel.annotation.get_bbox_patch().set(fc="white", alpha=0.95)
            return on_add
        cursor.connect("add", make_on_add(col, y_outliers, outlier_indices, datetimes))
