# # plotly_line_chart.py

# import plotly.graph_objs as go

# def plotly_line_chart(df, x, y, name=None):
#     fig = go.Figure()
#     fig.add_trace(go.Scatter(
#         x=x,
#         y=y,
#         mode='lines+markers',
#         name=name or y.name  # fallback nếu name không truyền
#     ))
#     fig.update_layout(
#         title="📈 Line Chart",
#         xaxis_title=str(x.name) if hasattr(x, 'name') else "X",
#         yaxis_title=str(y.name) if hasattr(y, 'name') else "Y",
#         template="plotly_white"
#     )
#     return fig


# plotly_line_chart.py
import plotly.graph_objs as go
import plotly.io as pio
import webbrowser
import tempfile
import os

def plotly_line_chart(df, x, y_columns, title="📈 Multi-Line Chart"):
    fig = go.Figure()
    for col in y_columns:
        if col in df.columns and not df[col].dropna().empty:
            fig.add_trace(go.Scatter(
                x=df[x],
                y=df[col],
                mode='lines+markers',
                name=col
            ))

    fig.update_layout(
        title=title,
        xaxis_title=x,
        yaxis_title="Giá trị",
        template="plotly_white",
        height=400 + 30 * len(y_columns)  # Tăng chiều cao nếu nhiều biến
    )

    # Save ra 1 file tạm thời
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    pio.write_html(fig, file=tmp_file.name, auto_open=True)
    # webbrowser.open(f"file://{tmp_file.name}")

