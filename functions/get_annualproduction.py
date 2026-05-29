from www.services import *


def get_annual_production(df):
    """
    Generate a plot of annual scientific production.
    
    Args:
        df: A DataFrame object containing the data.
        
    Returns:
        A Plotly figure object representing the annual scientific production.
    """
    data = df.get()

    # Filter out invalid years (<= 1800)
    valid_data = data[data["PY"] > 1800]
    if valid_data.empty:
        valid_data = data

    # Calculate the number of publications per year
    publications_per_year = valid_data["PY"].value_counts().sort_index().reset_index()
    publications_per_year.columns = ["Year", "Freq"]

    # Find the range of years
    min_year = int(publications_per_year["Year"].min())
    max_year = int(publications_per_year["Year"].max())

    # Ensure all years in the range are present
    all_years = pd.DataFrame({"Year": range(min_year, max_year + 1)})
    publications_per_year = all_years.merge(publications_per_year, on="Year", how="left").fillna(0)

    # Create the plot
    fig = px.line(
        publications_per_year, x="Year", y="Freq",
        labels={"Year": "Year", "Freq": "Articles"},
        markers=True
    )

    # Customize the layout and tooltips (hover)
    fig.update_traces(
        line=dict(color='#5567BB', width=3),
        marker=dict(size=8, color='#1f77b4', line=dict(width=1, color='white')),
        hovertemplate=(
            "<b>Year:</b> %{x}<br>"
            "<b>Articles:</b> %{y}<extra></extra>"
        )
    )

    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=publications_per_year["Year"][::2],  # Show every second year
            showline=True,
            linewidth=1,
            linecolor='#CCCCCC',
            mirror=True,
            ticks='outside',
            tickfont=dict(size=13)
        ),
        yaxis=dict(
            title="Articles",
            showline=True,
            linewidth=1,
            linecolor='#CCCCCC',
            mirror=True,
            ticks='outside',
            tickfont=dict(size=13),
            zeroline=True,
            zerolinecolor='#E0E0E0'
        ),
        xaxis_title="Year",
        plot_bgcolor='white',
        font=dict(color="#222222", size=14, family="Segoe UI, Arial"),
        margin=dict(l=50, r=30, t=60, b=50),
        height=600,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#1f77b4"
        )
    )

    # Customize the grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, publications_per_year
