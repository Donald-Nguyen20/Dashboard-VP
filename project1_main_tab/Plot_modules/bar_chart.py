from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def _hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple (0-1 range)"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    """Convert RGB tuple (0-1 range) to hex color"""
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))


def _lighten_color(hex_color, amount=0.3):
    """Lighten a hex color by blending with white"""
    rgb = _hex_to_rgb(hex_color)
    # Blend towards white (1, 1, 1)
    lightened = tuple(min(1.0, c + (1 - c) * amount) for c in rgb)
    return lightened


def _lighter_color(base_color, n_ranges):
    """Generate n_ranges of progressively lighter shades of base_color"""
    if base_color is None:
        base_color = "#1976d2"  # default
    
    colors = []
    for i in range(n_ranges):
        # Create progressively lighter shades
        amount = i * (0.7 / max(1, n_ranges - 1))  # 0 to 0.7 lightening
        color = _lighten_color(base_color, amount)
        colors.append(color)
    return colors


def _annotate_bars(ax, rects, labels=None, fmt="{:.2f}", num_vars=1):
    """Helper to annotate bars with given labels or their heights.
    Font size scales with bar width and number of variables."""
    if not rects:
        return
    
    # Find the max bar width to normalize font sizing
    max_width = max(rect.get_width() for rect in rects)
    
    # Scale base font size inversely with number of variables
    # More vars = smaller font, fewer vars = larger font
    base_font = max(6, 12 - (num_vars - 1) * 0.5)  # ranges from 12 down
    
    for i, rect in enumerate(rects):
        h = rect.get_height()
        if labels is not None:
            text = fmt.format(labels[i])
        else:
            text = fmt.format(h)
        
        # Scale font size based on bar width (relative to max_width)
        if max_width > 0:
            width_ratio = rect.get_width() / max_width
            font_size = max(6, min(base_font, base_font * width_ratio * 1.2))
        else:
            font_size = base_font
        
        ax.text(rect.get_x() + rect.get_width() / 2, h, text,
                ha='center', va='bottom', fontsize=font_size, rotation=0)



def plot_bar_chart(plot_tab, df: pd.DataFrame, time_ranges=None):
    """Draw a grouped or single bar chart and annotate each bar with max value.

    - If time_ranges is provided: plot side-by-side bars for each time range
    - If a `hue` is selected, bars show group means but annotated with each group's max.
    - If `Datetime` exists and exactly one variable selected, bars are daily-aggregated means
      and annotated with daily maxima.
    - Otherwise bars show mean per variable and are annotated with the max per variable.
    
    Args:
        plot_tab: Reference to PlotTab instance
        df: Full DataFrame (not filtered)
        time_ranges: List of (start_dt, end_dt) tuples for multi-range comparison, or None
    """
    if df is None or df.empty:
        return

    vars = list(plot_tab.selected_vars)
    ax = plot_tab.ax
    ax.clear()

    # Multi-range mode: plot side-by-side bars for each range
    if time_ranges is not None and len(time_ranges) > 1:
        if 'Datetime' not in df.columns:
            return
        
        # Filter data for each range and compute means/maxs
        range_data = []
        for start_dt, end_dt in time_ranges:
            df_range = df[(df['Datetime'] >= start_dt) & (df['Datetime'] <= end_dt)]
            if df_range.empty:
                continue
            means = df_range[vars].mean()
            maxs = df_range[vars].max()
            range_data.append({'means': means, 'maxs': maxs, 'label': f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}"})
        
        if not range_data:
            return
        
        # Plot side-by-side bars
        n_vars = len(vars)
        n_ranges = len(range_data)
        indices = np.arange(n_vars)
        width = 0.8 / max(1, n_ranges)
        
        # Get base color from plot_tab, generate lighter shades
        base_color = getattr(plot_tab, 'bar_color', None)
        colors_palette = _lighter_color(base_color, n_ranges)
        
        for r_idx, range_info in enumerate(range_data):
            heights = range_info['maxs'].values
            rects = ax.bar(indices + r_idx * width, heights, width, 
                          label=range_info['label'], color=colors_palette[r_idx])
            # Annotate with max values on top
            max_vals = range_info['maxs'].values
            _annotate_bars(ax, rects, labels=max_vals, fmt="{:.2f}", num_vars=n_vars)
        
        ax.set_xticks(indices + width * (n_ranges - 1) / 2)
        ax.set_xticklabels(vars, rotation=30 if len(vars) > 3 else 0)
        ax.set_title(f'Bar Comparison ({n_ranges} ranges)')
        ax.set_ylabel('Mean')
        ax.legend()
        plot_tab.canvas.draw()
        return

    # Original single-range logic continues below
    hue_text = plot_tab.hue_combo.currentText()
    use_hue = hue_text != "❌ Không phân loại"

    # Single variable with Datetime -> daily bars (mean) annotated with daily max
    if 'Datetime' in df.columns and len(vars) == 1:
        col = vars[0]
        df_loc = df.set_index('Datetime')
        if pd.api.types.is_numeric_dtype(df_loc[col]):
            mean_series = df_loc[col].resample('D').mean()
            max_series = df_loc[col].resample('D').max()
        else:
            mean_series = df_loc[col].resample('D').agg(lambda s: s.value_counts().idxmax() if len(s) > 0 else None)
            max_series = mean_series.copy()

        x = mean_series.index
        y = mean_series.values
        # use selected color from plot_tab if available
        color = getattr(plot_tab, 'bar_color', None)
        if color:
            rects = ax.bar(x, y, color=color)
        else:
            rects = ax.bar(x, y)
        # annotate with daily max values
        max_vals = max_series.values
        _annotate_bars(ax, rects, labels=max_vals, fmt="{:.2f}", num_vars=1)

        ax.set_title(f"Bar: {col} (daily)")
        ax.set_xlabel('Datetime')
        ax.set_ylabel(col)
        plot_tab.canvas.draw()
        return

    # Grouped bars by hue: plot group means but annotate with group-wise max
    if use_hue and hue_text in df.columns:
        hue_col = hue_text
        grouped_mean = df.groupby(hue_col)[vars].mean()
        grouped_max = df.groupby(hue_col)[vars].max()
        categories = grouped_mean.index.astype(str).tolist()
        n_cat = len(categories)
        n_vars = len(vars)
        indices = np.arange(n_cat)
        width = 0.8 / max(1, n_vars)

        # keep all rects to annotate
        # get base color if provided and generate per-variable colors
        base_color = getattr(plot_tab, 'bar_color', None)
        colors = None
        if base_color and len(vars) > 1:
            import matplotlib.colors as mcolors
            cmap = mcolors.LinearSegmentedColormap.from_list('base', ['white', base_color])
            colors = [cmap(i / max(1, len(vars) - 1)) for i in range(len(vars))]

        for i, var in enumerate(vars):
            heights = grouped_mean[var].values
            kw = {'label': var, 'width': width}
            if colors is not None:
                kw['color'] = colors[i]
            rects = ax.bar(indices + i * width, heights, **kw)
            # annotate using grouped_max
            max_vals = grouped_max[var].values
            _annotate_bars(ax, rects, labels=max_vals, fmt="{:.2f}", num_vars=n_vars)

        ax.set_xticks(indices + width * (n_vars - 1) / 2)
        ax.set_xticklabels(categories, rotation=30)
        ax.set_title('Bar by ' + hue_col)
        ax.legend()
        plot_tab.canvas.draw()
        return

    # Default: bar of mean value per variable, annotate with max per variable
    means = df[vars].mean()
    maxs = df[vars].max()
    color = getattr(plot_tab, 'bar_color', None)
    if color:
        rects = ax.bar(vars, means.values, color=color)
    else:
        rects = ax.bar(vars, means.values)
    _annotate_bars(ax, rects, labels=maxs.values, fmt="{:.2f}", num_vars=len(vars))
    ax.set_title('Mean value per variable')
    ax.set_ylabel('Mean')
    plot_tab.canvas.draw()
