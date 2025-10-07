def plotly_scatter2d(df, x, y):
    import plotly.graph_objs as go
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x],
        y=df[y],
        mode='markers',
        marker=dict(size=10, color='blue'),
        name=f"{y} vs {x}"
    ))
    fig.update_layout(
        title="📍 Scatter Plot",
        xaxis_title=x,
        yaxis_title=y,
        template="plotly_white"
    )
    return fig
