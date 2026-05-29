from www.services import *


def get_sources_production(df, num_of_sources_production, occurences):
    """
    Generate a plot of sources' production over time.

    Args:
        df: A DataFrame object containing the data.
        num_of_sources_production: The number of top sources to display.
        occurences: A string indicating whether to display cumulative occurrences.

    Returns:
        A Plotly figure object representing the sources' production over time.
    """
    class FilteredDF:
        def __init__(self, val):
            self.val = val
        def get(self):
            return self.val

    raw_data = df.get()
    # Filter out invalid years (<= 1800)
    data = raw_data[raw_data["PY"] > 1800].copy()
    if data.empty:
        data = raw_data.copy()

    filtered_df = FilteredDF(data)

    # Calculate the number of publications per year for each source
    WSO = cocMatrix(filtered_df, Field="SO")
    if WSO.shape[1] == 1:
        WSO = pd.DataFrame(WSO, columns=[data["SO"].iloc[0]])

    if num_of_sources_production > WSO.shape[1]:
        num_of_sources_production = WSO.shape[1]

    data["PY"] = data["PY"].astype(str)
    WPY = cocMatrix(filtered_df, Field="PY")
    data["PY"] = data["PY"].astype(int)

    missing_years = set(range(data["PY"].min(), data["PY"].max() + 1)) - set(WPY.columns.astype(int))
    if missing_years:
        for year in missing_years:
            WPY[str(year)] = 0

    WPY = WPY[sorted(WPY.columns.astype(int).astype(str))]

    PYSO = WPY.T.dot(WSO)
    ind = PYSO.sum(axis=0)
    top_sources = ind.nlargest(num_of_sources_production).index
    PYSO = PYSO[top_sources]

    if occurences == "cumulative":
        PYSO = PYSO.cumsum()
        y_label = "Cumulative occurrences"
    else:
        y_label = "Annual occurrences"

    PYSO = PYSO.reset_index().rename(columns={"index": "Year"})

    # Melt data for plotting
    melted_growth = PYSO.melt(id_vars="Year", var_name="Source", value_name="Freq")

    # Create the plot
    fig = px.line(
        melted_growth,
        x="Year",
        y="Freq",
        color="Source",
        labels={"Year": "Year", "Freq": y_label, "Source": "Source"},
    )

    # Customize the layout and tooltips (hover)
    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=PYSO["Year"].unique()[::max(1, len(PYSO["Year"].unique()) // 20)]
        ),
        yaxis_title=y_label,
        xaxis_title="Year",
        plot_bgcolor='white',
        title_font_size=24,
        font=dict(color="#444444"),
        margin=dict(l=40, r=40, t=40, b=40),
        height=800,
        legend=dict(
            title="Source",
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        )
    )

    # Customize the hover template for each trace
    fig.update_traces(
        hovertemplate=(
            "<b>Source:</b> %{name}<br>"
            "<b>Year:</b> %{x}<br>"
            "<b>Occurrences:</b> %{y}<extra></extra>"
        )
    )

    # Customize the grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, PYSO
