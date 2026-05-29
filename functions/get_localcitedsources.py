from www.services import *


def get_local_cited_sources(df, num_of_cited_sources):
    """
    Generate a plot and table of the most local cited sources.
    
    Args:
        input: An object that provides user input methods.
        df: A DataFrame object containing the data.
        num_of_cited_sources: The number of top cited sources to display.
        
    Returns:
        A Plotly figure object and a DataFrame of the most local cited sources.
    """
    # Extract metadata tags for cited sources
    df = metaTagExtraction(df, "CR_SO")

    data = df.get()
    
    if isinstance(data["CR_SO"].iloc[0], list):  # Check if the first element is a list
        # Flatten the 'CR_SO' column containing lists
        exploded = data["CR_SO"].explode().dropna()
        exploded = exploded[exploded.apply(lambda x: isinstance(x, str) and x.strip() != "")]
        exploded = exploded.str.upper()
        if len(exploded) == 0:
            source_counts = pd.DataFrame(columns=["Sources", "N. of Local Citations"])
        else:
            source_counts = exploded.value_counts().reset_index()
            source_counts.columns = ["Sources", "N. of Local Citations"]
    else:
        # If not a list, continue with the string method
        exploded = data["CR_SO"].str.split(";").explode().dropna()
        exploded = exploded[exploded.apply(lambda x: isinstance(x, str) and x.strip() != "")]
        exploded = exploded.str.upper()
        source_counts = exploded.value_counts().reset_index()
        source_counts.columns = ["Sources", "N. of Local Citations"]

    # Limit the number of sources to display
    if len(source_counts) == 0:
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text="No cited sources data available",
                            x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
            plot_bgcolor='white', height=300
        )
        fig = go.FigureWidget(fig)
        return fig, source_counts

    if num_of_cited_sources > len(source_counts):
        num_of_cited_sources = len(source_counts)

    # Prepare the complete table and filter rows for display
    table_located_sources = source_counts.copy()
    source_counts = source_counts.head(num_of_cited_sources)
    

    # Truncate long source names and add line breaks every 50 characters
    def wrap_label(label, width=50):
        return '<br>'.join([label[i:i+width] for i in range(0, len(label), width)])
    source_counts["Sources_wrapped"] = source_counts["Sources"].apply(wrap_label)

    # Create the plot (use scatter instead of scatter with orientation='h')
    fig = go.Figure()

    # Add the main scatter plot
    fig.add_trace(
        go.Scatter(
            x=source_counts["N. of Local Citations"],
            y=list(range(len(source_counts))),
            mode="markers+text",
            marker=dict(
                size=18 + 6 * (source_counts["N. of Local Citations"] / source_counts["N. of Local Citations"].max()),
                color=source_counts["N. of Local Citations"],
                colorscale=[[0, "#B3D1F2"], [1, "#5567BB"]],
                line=dict(width=1, color="#E0E0E0"),
                opacity=0.95,
                showscale=False,
            ),
            text=source_counts["N. of Local Citations"],
            textposition="top center",  
            textfont=dict(color="#5567BB", size=13),  
            hovertemplate=(
                "<b>Source:</b> %{customdata}<br>"
                "<b>N. of Local Citations:</b> %{x}<extra></extra>"
            ),
            customdata=source_counts["Sources_wrapped"],
        )
    )

    # Add a thick line from label (x=0) to the marker for each source
    for i, x_val in enumerate(source_counts["N. of Local Citations"]):
        fig.add_shape(
            type="line",
            x0=0,
            x1=x_val,
            y0=i,
            y1=i,
            line=dict(color="#E0E0E0", width=4),
            layer="below",
        )

    # Add horizontal grid lines for each source (lighter)
    for i in range(len(source_counts)):
        fig.add_shape(
            type="line",
            x0=0,
            x1=source_counts["N. of Local Citations"].max(),
            y0=i,
            y1=i,
            line=dict(color="#E0E0E0", width=2),
            layer="below",
        )

    # Set x-axis ticks to 0, 50, 100, etc.
    max_x = source_counts["N. of Local Citations"].max()
    tick_step = 50
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
        title="N. of Local Citations",
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
    
    return fig, table_located_sources
