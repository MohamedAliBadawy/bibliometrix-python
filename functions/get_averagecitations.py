from www.services import *


def get_average_citations(df):
    """
    Generate a plot of average citations per year.
    
    Args:
        df: A DataFrame object containing the data.
        
    Returns:
        A Plotly figure object representing the average citations per year.
    """
    data = df.get()

    # Filter out invalid years (<= 1800)
    valid_data = data[data["PY"] > 1800]
    if valid_data.empty:
        valid_data = data

    # Calculate the current year
    current_year = pd.Timestamp.now().year + 1

    # Group by publication year and calculate mean total citations per article
    table = valid_data.groupby("PY").agg(
        MeanTCperArt=("TC", lambda x: round(x.mean(), 2)),
        N=("PY", "count")
    ).reset_index()

    # Calculate mean total citations per year and citable years
    table["MeanTCperYear"] = round(table["MeanTCperArt"] / (current_year - table["PY"]), 2)
    table["CitableYears"] = current_year - table["PY"]
    table = table.dropna().rename(columns={"PY": "Year"})

    # Create the plot
    fig = px.line(table, x="Year", y="MeanTCperYear", 
                  labels={"Year": "Year", "MeanTCperYear": "Average Citations per Year"},
                  markers=True)

    # Customize the layout and tooltips (hover)
    fig.update_traces(
        line=dict(color='#5567BB', width=3),
        marker=dict(size=8, color='#1f77b4', line=dict(width=1, color='white')),
        hovertemplate=(
            "<b>Year:</b> %{x}<br>"
            "<b>Avg. Citations/Year:</b> %{y}<br>"
            "<b>Articles:</b> %{customdata[0]}<br>"
            "<b>Mean Citations/Article:</b> %{customdata[1]}<extra></extra>"
        ),
        customdata=table[["N", "MeanTCperArt"]].values
    )

    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=table["Year"][::2],  # Show every second year
            showline=True,
            linewidth=1,
            linecolor='#CCCCCC',
            mirror=True,
            ticks='outside',
            tickfont=dict(size=13)
        ),
        yaxis=dict(
            title="Average Citations per Year",
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
            bordercolor="#5567BB"
        )
    )

    # Customize the grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, table
