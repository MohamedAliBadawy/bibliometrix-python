from www.services import *


def get_cited_countries(df, num_of_cited_countries, cited_countries_measure):
    """
    Generate a plot and table of the most cited countries.
    
    Args:
        df: A DataFrame object containing the data.
        num_of_cited_countries: The number of top cited countries to display.
        cited_countries_measure: The measure to use for ranking (either "TC" for total citations or "Average Article Citations").
        
    Returns:
        A Plotly figure object and a DataFrame of the most cited countries.
    """
    # Extract metadata tags for cited countries
    df = metaTagExtraction(df, "AU1_CO")
    df = df.get()

    # Prepare the table for ranking countries
    tab = (
        df.dropna(subset=["AU1_CO"])
        .groupby("AU1_CO", as_index=False)
        .agg(TotalCitation=("TC", "sum"), AverageArticleCitations=("TC", lambda x: round(x.sum() / len(x), 1)))
        .rename(columns={"AU1_CO": "Country"})
        .sort_values(by="TotalCitation", ascending=False)
    )

    # Guard: no country data available (e.g. Lens exports without affiliations)
    if tab.empty:
        empty_df = pd.DataFrame(columns=["Country", "TotalCitation", "AverageArticleCitations"])
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(
                text="Country data not available for this database.<br>Affiliation/address fields are required to extract countries.",
                x=0.5, y=0.5, showarrow=False, font=dict(size=15), align="center"
            )],
            plot_bgcolor='white', height=300
        )
        fig = go.FigureWidget(fig)
        fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'], 'displaylogo': False}
        return fig, empty_df

    # Convert columns to numeric to ensure correct calculations
    tab["TotalCitation"] = pd.to_numeric(tab["TotalCitation"])
    tab["AverageArticleCitations"] = pd.to_numeric(tab["AverageArticleCitations"])
    tab = tab.sort_values(by="TotalCitation", ascending=False)
    table = tab
    tab = tab.head(num_of_cited_countries)

    # Select the appropriate measure based on user input
    if cited_countries_measure == "total_cit":
        tab = tab[["Country", "TotalCitation"]]
        laby = "N. of Citations"
    else:
        tab = tab.sort_values(by="AverageArticleCitations", ascending=False)[["Country", "AverageArticleCitations"]]
        laby = "Average Article Citations"

    # Prepare data for plotting
    tab = tab.reset_index(drop=True)
    y_labels = tab["Country"]
    x_values = tab.iloc[:, 1]
    n = len(tab)

    fig = go.Figure()

    # Add thick lines from y-label to marker
    for i, (country, value) in enumerate(zip(y_labels, x_values)):
        fig.add_shape(
            type="line",
            x0=0,
            x1=value,
            y0=i,
            y1=i,
            line=dict(color="#e0e0e0", width=5),
            layer="below",
        )

    # Add scatter markers with text
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=list(range(n)),
            mode="markers+text",
            marker=dict(
                size=18 + 6 * (x_values / max(x_values.max(), 1)),
                color=x_values,
                colorscale=[[0, "#B3D1F2"], [1, "#5567BB"]],
                line=dict(width=1, color="#E0E0E0"),
                opacity=0.95,
                showscale=False,
            ),
            text=x_values,
            textposition="top center",
            textfont=dict(color="#5567BB", size=13),
            hovertemplate=(
                "<b>Country:</b> %{customdata}<br>"
                "<b>" + laby + ":</b> %{x}<extra></extra>"
            ),
            customdata=y_labels,
        )
    )

    # Add horizontal grid lines for each country
    for i in range(n):
        fig.add_shape(
            type="line",
            x0=0,
            x1=x_values.max(),
            y0=i,
            y1=i,
            line=dict(color="#E0E0E0", width=2),
            layer="below",
        )

    # Set x-axis ticks
    max_x = x_values.max()
    tick_step = 5 if max_x <= 50 else int(max_x // 10) or 1
    x_ticks = list(range(0, int(max_x) + tick_step, tick_step))
    if x_ticks[-1] < max_x:
        x_ticks.append(int(max_x))

    fig.update_yaxes(
        tickvals=list(range(n)),
        ticktext=y_labels,
        autorange="reversed",
        showgrid=False,
        title="Country",
        tickfont=dict(size=13),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F0F0F0",
        zeroline=False,
        tickvals=x_ticks,
        title=laby,
        tickfont=dict(size=13),
    )
    fig.update_layout(
        plot_bgcolor='white',
        font=dict(color="#222222", size=14, family="Segoe UI, Arial"),
        margin=dict(l=0, r=0, t=0, b=0),
        height=50 + 90 * n,
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
    
    return fig, table
