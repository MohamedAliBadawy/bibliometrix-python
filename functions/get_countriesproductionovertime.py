from www.services import *


def get_countries_production_over_time(df, top_k_countries):
    """
    Generate a plot of country's production over time.

    Args:
        df: A DataFrame object containing the data.
        top_k_countries: The number of top countries to display.  

    Returns:
        A Plotly figure object representing the country's production over time.
    """
    df = metaTagExtraction(df, "AU_CO")
    data = df.get()

    # Filter out invalid years (<= 1800)
    data = data[data["PY"] > 1800]

    AFF = pd.Series(data["AU_CO"]).dropna().apply(lambda x: [aff.strip() for aff in x if aff.strip() != ""])
    nAFF = [len(aff) for aff in AFF]

    affiliations = [aff for sublist in AFF for aff in sublist]
    years = data["PY"].repeat(nAFF).values[:len(affiliations)]
    AFFY = pd.DataFrame({
        "Affiliation": affiliations,
        "Year": years
    }).query('Affiliation != "NA"').dropna(subset=["Affiliation", "Year"])

    AFFY = AFFY.groupby(["Affiliation", "Year"]).size().reset_index(name="Articles")
    AFFY = AFFY.pivot(index="Affiliation", columns="Year", values="Articles").fillna(0)
    AFFY = AFFY.stack().reset_index(name="Articles")
    AFFY["Articles"] = AFFY.groupby("Affiliation")["Articles"].cumsum()

    Affselected = AFFY[AFFY["Year"] == AFFY["Year"].max()].nlargest(top_k_countries, "Articles")

    AffOverTime = AFFY[AFFY["Affiliation"].isin(Affselected["Affiliation"])]
    AffOverTime["Year"] = AffOverTime["Year"].astype(int)
    AffOverTime = AffOverTime.rename(columns={"Affiliation": "Country"})

    # Create the plot
    fig = px.line(
        AffOverTime,
        x="Year",
        y="Articles",
        color="Country",
        labels={"Year": "Year", "Articles": "Cumulative Articles", "Country": "Country"},
    )

    # Customize the layout
    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=AffOverTime["Year"].unique()[::max(1, len(AffOverTime["Year"].unique()) // 20)]
        ),
        yaxis_title="Cumulative Articles",
        xaxis_title="Year",
        plot_bgcolor='white',
        title_font_size=24,
        font=dict(color="#444444"),
        margin=dict(l=40, r=40, t=40, b=40),
        height=600,
        legend=dict(
            title="Country",
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        )
    )

    # Customize the grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, AffOverTime
