from www.services import *


def get_relevant_affiliations(df, num_of_affiliations, disambiguation):
    """
    Generate a plot and table of the most relevant authors with frequency options.
    
    Args:
        df: A DataFrame object containing the data.
        num_of_authors: The number of top authors to display.
        frequency: Type of frequency calculation. Options: "N. of Documents", "Percentage", "Fractionalized".
        
    Returns:
        A Plotly figure object and a DataFrame of the most relevant authors.
    """
    data = df.get()

    import unicodedata

    def strip_accents(s):
        if not isinstance(s, str):
            return s
        return "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    if disambiguation == "yes":
        metaTagExtraction(df, "AU_UN", aff_disamb=True)
        data = df.get()
        # Extract affiliations from the "AU_UN" field, splitting by semicolon first
        aff_series = data["AU_UN"].astype(str).str.split(";").explode().dropna()
        aff_series = aff_series.str.strip().str.upper()
        aff_series = aff_series.apply(strip_accents)
        affiliations = aff_series[~aff_series.isin(["", "NOTREPORTED", "NOTDECLARED", "NAN", "NONE"])]
    else:
        # Extract affiliations from the "C1" field
        aff_series = data["C1"].explode().dropna().astype(str)
        # Remove bracketed author prefixes (like "[Author, A] ") commonly found in WoS
        aff_series = aff_series.str.replace(r"^\[.*?\]\s*", "", regex=True)
        aff_series = aff_series.str.strip().str.upper()
        aff_series = aff_series.apply(strip_accents)
        affiliations = aff_series[~aff_series.isin(["", "NAN", "NONE"])]

    # Count occurrences of each affiliation
    affiliation_counts = affiliations.value_counts().reset_index()
    affiliation_counts.columns = ["Affiliation", "Articles"]

    # Limit the number of affiliations to display
    if num_of_affiliations > len(affiliation_counts):
        num_of_affiliations = len(affiliation_counts)
    affiliation_counts = affiliation_counts.head(num_of_affiliations)

    # Create the plot
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=affiliation_counts["Articles"],
            y=list(range(len(affiliation_counts))),
            mode="markers+text",
            marker=dict(
                size=18 + 6 * (affiliation_counts["Articles"] / affiliation_counts["Articles"].max()),
                color=affiliation_counts["Articles"],
                colorscale=[[0, "#B3D1F2"], [1, "#5567BB"]],
                line=dict(width=1, color="#E0E0E0"),
                opacity=0.95,
                showscale=False,
            ),
            text=affiliation_counts["Articles"],
            textposition="top center",
            textfont=dict(color="#5567BB", size=13),
            hovertemplate=(
                "<b>Affiliation:</b> %{customdata}<br>"
                "<b>Articles:</b> %{x}<extra></extra>"
            ),
            customdata=affiliation_counts["Affiliation"],
        )
    )

    fig.update_layout(
        yaxis=dict(
            autorange="reversed",
            showgrid=True,
            gridcolor="lightgrey",
            zeroline=False,
            tickmode='array',
            tickvals=list(range(len(affiliation_counts))),
            ticktext=affiliation_counts["Affiliation"]
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="lightgrey",
            zeroline=False,
            tick0=5,
            dtick=5,
            title="Articles"
        ),
        plot_bgcolor='white',
        title_font_size=24,
        font=dict(color="#444444"),
        margin=dict(l=200, r=40, t=40, b=40),
        height=800,
        showlegend=False
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, affiliation_counts
