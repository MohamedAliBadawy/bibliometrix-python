from www.services import *


def get_local_cited_refs(df, num_of_cited_refs, field_separator):
    """
    Generate a plot and table of the most local cited sources.
    
    Args:
        df: A DataFrame object containing the data.
        num_of_cited_refs: The number of top cited sources to display.
        field_separator: The separator used in the citations field.
        
    Returns:
        A Plotly figure object and a DataFrame of the most local cited sources.
    """
    data = df.get()

    import re as _re
    _lens_id_pat = _re.compile(r'^[0-9A-Z]{3}-[0-9A-Z]{3}-[0-9A-Z]{3}-[0-9A-Z]{3}-[0-9A-Z]{3,4}X?$')
    db_val = str(data["DB"].iloc[0]).upper() if len(data) > 0 else ""

    if isinstance(data["CR"].iloc[0], list):  # Check if the first element is a list
        # Flatten the 'CR' column containing lists
        exploded = pd.DataFrame(data["CR"].explode())
        # Filter out empty strings and NaN values
        exploded = exploded[exploded["CR"].apply(lambda x: isinstance(x, str) and x.strip() != "")]
        if len(exploded) == 0:
            source_counts = pd.DataFrame(columns=["Cited References", "Citations"])
        else:
            # Normalize to uppercase and strip outer whitespace (exactly like R)
            exploded["CR"] = exploded["CR"].str.upper().str.strip()

            # For Lens: filter out raw unresolved Lens IDs before counting
            if db_val == "LENS":
                exploded = exploded[~exploded["CR"].apply(
                    lambda x: bool(_lens_id_pat.match(str(x).strip()))
                )]

            # Robust filter: Must contain at least one letter and have length >= 15 characters
            exploded = exploded[
                exploded["CR"].str.contains(r"[A-Z]", na=False) &
                (exploded["CR"].str.len() >= 15)
            ]

            source_counts = (
                exploded.value_counts()
                .reset_index()
            )
            source_counts.columns = ["Cited References", "Citations"]
    else:
        # If not a list, continue with the string method
        exploded = data["CR"].str.split(field_separator).explode()
        exploded = exploded.dropna().str.upper().str.strip()
        # For Lens: filter out raw unresolved Lens IDs before counting
        if db_val == "LENS":
            exploded = exploded[~exploded.apply(lambda x: bool(_lens_id_pat.match(str(x).strip())))]
        exploded = exploded[(exploded != "") & (exploded.str.len() >= 15) & (exploded.str.contains(r"[A-Z]", na=False))]
        source_counts = exploded.value_counts().reset_index()
        source_counts.columns = ["Cited References", "Citations"]

    # Filter out unwanted references
    source_counts = source_counts[source_counts["Cited References"] != "ANONYMOUS, NO TITLE CAPTURED"]

    # Handle empty results
    if len(source_counts) == 0:
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text="No cited references data available",
                            x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
            plot_bgcolor='white', height=300
        )
        fig = go.FigureWidget(fig)
        return fig, source_counts

    # Limit the number of sources to display
    if num_of_cited_refs > len(source_counts):
        num_of_cited_refs = len(source_counts)

    # Truncate source names to 70 characters
    source_counts["Cited References"] = source_counts["Cited References"].str[:70]

    # Prepare the complete table and filter rows for display
    table_located_sources = source_counts.copy()
    source_counts = source_counts.head(num_of_cited_refs)
    
    # Create the plot (use scatter instead of scatter with orientation='h')
    fig = go.Figure()

    # Add a thick line from each label to its marker
    for i, row in source_counts.iterrows():
        fig.add_shape(
            type="line",
            x0=0,
            x1=row["Citations"],
            y0=i,
            y1=i,
            line=dict(color="#e0e0e0", width=5),
            layer="below",
        )

    fig.add_trace(
        go.Scatter(
            x=source_counts["Citations"],
            y=list(range(len(source_counts))),
            mode="markers+text",
            marker=dict(
                size=18 + 6 * (source_counts["Citations"] / source_counts["Citations"].max()),
                color=source_counts["Citations"],
                colorscale=[[0, "#B3D1F2"], [1, "#5567BB"]],
                line=dict(width=1, color="#E0E0E0"),
                opacity=0.95,
                showscale=False,
            ),
            text=source_counts["Citations"],
            textposition="top center",
            textfont=dict(color="#5567BB", size=13),
            hovertemplate=(
                "<b>Reference:</b> %{customdata}<br>"
                "<b>Citations:</b> %{x}<extra></extra>"
            ),
            customdata=source_counts["Cited References"],
        )
    )

    # Add horizontal grid lines for each reference (lighter)
    for i in range(len(source_counts)):
        fig.add_shape(
            type="line",
            x0=0,
            x1=source_counts["Citations"].max(),
            y0=i,
            y1=i,
            line=dict(color="#E0E0E0", width=2),
            layer="below",
        )

    # Set x-axis ticks to 0, 5, 10, etc.
    max_x = source_counts["Citations"].max()
    tick_step = 5
    x_ticks = list(range(0, int(max_x) + tick_step, tick_step))
    if x_ticks[-1] < max_x:
        x_ticks.append(int(max_x))

    fig.update_yaxes(
        tickvals=list(range(len(source_counts))),
        ticktext=source_counts["Cited References"],
        autorange="reversed",
        showgrid=False,
        title="References",
        tickfont=dict(size=13),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F0F0F0",
        zeroline=False,
        tickvals=x_ticks,
        title="Citations",
        tickfont=dict(size=13),
    )
    fig.update_layout(
        plot_bgcolor='white',
        font=dict(color="#222222", size=14, family="Segoe UI, Arial"),
        margin=dict(l=0, r=0, t=0, b=0),
        height=50 + 90 * len(source_counts),
        showlegend=False,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),
        coloraxis_showscale=False,
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}
    
    return fig, table_located_sources
