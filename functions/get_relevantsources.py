from www.services import *


def get_relevant_sources(df, num_of_sources):
    """
    Generate a plot and table of the most relevant sources.
    
    Args:
        df: A DataFrame object containing the data.
        num_of_sources: The number of top sources to display.
        
    Returns:
        A Plotly figure object and a DataFrame of the most relevant sources.
    """
    data = df.get()

    # Drop rows with missing values
    data = data.dropna(subset=["SO"])

    # Ensure SO is string
    data["SO"] = data["SO"].apply(lambda x: x[0] if isinstance(x, list) and x else str(x) if x else "")

    # Filter out empty SO
    data = data[data["SO"] != ""]

    if data.empty:
        return None, None  # or some default

    # Count the occurrences of each source
    source_counts = data["SO"].value_counts().reset_index()
    source_counts.columns = ["Sources", "N. of Documents"]
    # Truncate source names to 50 characters
    # source_counts["Sources"] = source_counts["Sources"].str[:50]
    table_relevant_sources = source_counts

    # Limit the number of sources to display
    if num_of_sources > len(source_counts):
        num_of_sources = len(source_counts)
    source_counts = source_counts.head(num_of_sources)

    # Truncate long source names and add line breaks every 50 characters
    def wrap_label(label, width=50):
        return '<br>'.join([label[i:i+width] for i in range(0, len(label), width)])
    source_counts["Sources_wrapped"] = source_counts["Sources"].apply(wrap_label)

    # Create the plot (use scatter instead of scatter with orientation='h')
    fig = go.Figure()

    # Add a thick line from each label to its marker
    for i, row in source_counts.iterrows():
        fig.add_shape(
            type="line",
            x0=0,
            x1=row["N. of Documents"],
            y0=i,
            y1=i,
            line=dict(color="#e0e0e0", width=5),
            layer="below",
        )

    fig.add_trace(
        go.Scatter(
            x=source_counts["N. of Documents"],
            y=list(range(len(source_counts))),
            mode="markers+text",
            marker=dict(
                size=18 + 6 * (source_counts["N. of Documents"] / source_counts["N. of Documents"].max()),
                color=source_counts["N. of Documents"],
                colorscale=[[0, "#B3D1F2"], [1, "#5567BB"]],
                line=dict(width=1, color="#E0E0E0"),
                opacity=0.95,
                showscale=False,
            ),
            text=source_counts["N. of Documents"],
            textposition="top center",  
            textfont=dict(color="#5567BB", size=13),  
            hovertemplate=(
                "<b>Source:</b> %{y}<br>"
                "<b>N. of Documents:</b> %{x}<extra></extra>"
            ),
        )
    )

    # Add horizontal grid lines for each source (lighter)
    for i in range(len(source_counts)):
        fig.add_shape(
            type="line",
            x0=0,
            x1=source_counts["N. of Documents"].max(),
            y0=i,
            y1=i,
            line=dict(color="#E0E0E0", width=2),
            layer="below",
        )

    # Set x-axis ticks to 0, 5, 10, etc.
    max_x = source_counts["N. of Documents"].max()
    tick_step = 5
    x_ticks = list(range(0, int(max_x) + tick_step, tick_step))
    if x_ticks[-1] < max_x:
        x_ticks.append(int(max_x))

    fig.update_yaxes(
        tickvals=list(range(len(source_counts))),
        ticktext=source_counts["Sources_wrapped"],
        autorange="reversed",
        showgrid=False,
        title="Sources",
        tickfont=dict(size=13),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F0F0F0",
        zeroline=False,
        tickvals=x_ticks,
        title="N. of Documents",
        tickfont=dict(size=13),
    )
    fig.update_layout(
        plot_bgcolor='white',
        font=dict(color="#222222", size=14, family="Segoe UI, Arial"),
        margin=dict(l=220, r=40, t=60, b=40),
        height=50 + 90 * len(source_counts),
        showlegend=False,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, table_relevant_sources
