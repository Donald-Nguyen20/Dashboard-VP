def plot_histogram_chart(plot_tab, df):
    import pandas as pd
    import numpy as np
    from PySide6.QtWidgets import QMessageBox
    import mplcursors

    selected = plot_tab.selected_vars
    if not selected:
        QMessageBox.warning(plot_tab, "Cảnh báo", "Hãy chọn ít nhất 1 biến để vẽ histogram.")
        return

    num_vars = len(selected)
    ncols = 2 if num_vars > 1 else 1
    nrows = int(np.ceil(num_vars / ncols))

    plot_tab.figure.clear()
    axes = plot_tab.figure.subplots(nrows, ncols, squeeze=False)

    # Để gom tất cả các patch cho tooltip
    all_patches = []

    for idx, col in enumerate(selected):
        row, col_pos = divmod(idx, ncols)
        ax = axes[row][col_pos]
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            n, bins, patches = ax.hist(df[col].dropna(), bins=60, edgecolor='black', picker=True)
            ax.set_title(col)
            ax.set_xlabel('Value')
            ax.set_ylabel('Frequency')
            # Gắn data cho tooltip
            for rect, count, left, right in zip(patches, n, bins[:-1], bins[1:]):
                rect._hist_value = f"{col}\nKhoảng: [{left:.2f}, {right:.2f}]\nFrequency: {int(count)}"
            all_patches.extend(patches)
        else:
            ax.set_visible(False)

    plot_tab.figure.tight_layout()
    plot_tab.canvas.draw()
    plot_tab.ax = axes[0][0]

    # ⭐ Tạo tooltip cho tất cả các cột histogram
    cursor = mplcursors.cursor(all_patches, hover=True)
    @cursor.connect("add")
    def on_add(sel):
        rect = sel.artist
        sel.annotation.set_text(rect._hist_value)
        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)
