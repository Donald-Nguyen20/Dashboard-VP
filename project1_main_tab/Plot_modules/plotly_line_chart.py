# File: Plot_modules/plotly_line_chart.py

import plotly.graph_objs as go
import plotly.io as pio
from PySide6.QtWebEngineWidgets import QWebEngineView
import pandas as pd


# Ham nay giong cac ham plot_matplotlib, chi khac la dung Plotly + QWebEngineView

def plot_plotly_line(widget, df):
    # Xac minh du lieu
    if df.empty or not widget.selected_vars:
        return

    # Neu co cot Datetime thi chuyen ve datetime va dung lam truc X
    if 'Datetime' in df.columns:
        df['Datetime'] = pd.to_datetime(df['Datetime'], errors='coerce')
        x_data = df['Datetime']
    else:
        x_data = df.index

    # Tao Figure
    fig = go.Figure()
    for var in widget.selected_vars:
        if var in df.columns and not df[var].dropna().empty:
            fig.add_trace(go.Scatter(
                x=x_data,
                y=df[var],
                mode='lines+markers',
                name=var
            ))

    fig.update_layout(
        title="📈 Plotly Line Chart",
        xaxis_title="Time",
        yaxis_title="Value",
        legend_title="Variables",
        template="plotly_white",
        height=500
    )

    html = pio.to_html(fig, full_html=False)

    # Neu widget chua co web_view thi tao moi va gan vao layout
    if not hasattr(widget, 'web_view'):
        widget.web_view = QWebEngineView()
        widget.layout().addWidget(widget.web_view)

    # Hien thi web_view, an canvas matplotlib
    widget.web_view.setVisible(True)
    widget.web_view.setHtml(html)
    widget.canvas.setVisible(False)
    widget.toolbar.setVisible(False)