from www.services import *


def get_affiliation_production_over_time(df, top_k_affiliations):
    """
    Generate a cumulative production line chart of the top affiliations over time,
    aligned perfectly with the "Most Relevant Affiliations" metric.

    Args:
        df: A DataFrame object containing the data.
        top_k_affiliations: The number of top affiliations to display.  

    Returns:
        fig: A Plotly figure object representing the affiliation's production over time.
        aff_top_out: Table summarizing cumulative articles published per affiliation.
    """
    data = df.get()

    # Force metaTagExtraction to run with aff_disamb=True to utilize the enhanced AU_UN columns
    metaTagExtraction(df, "AU_UN", aff_disamb=True)
    data = df.get()

    # Ensure "PY" is numeric and valid (ignore years <= 1800)
    data["PY"] = pd.to_numeric(data["PY"], errors="coerce")
    data = data[data["PY"] > 1800]
    data = data.dropna(subset=["PY", "AU_UN"])

    import unicodedata

    def strip_accents(s):
        if not isinstance(s, str):
            return s
        return "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    def split_affiliations(x):
        if isinstance(x, list):
            res = []
            for item in x:
                if isinstance(item, str):
                    res.extend([a.strip() for a in item.split(";") if a.strip()])
                else:
                    res.append(str(item).strip())
            return res
        elif isinstance(x, str):
            return [a.strip() for a in x.split(";") if a.strip()]
        return []

    AFF = data["AU_UN"].dropna().apply(split_affiliations)
    # Filter out rows with empty affiliation lists
    AFF = AFF[AFF.apply(len) > 0]
    nAFF = [len(aff) for aff in AFF]

    if len(AFF) == 0:
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text="No affiliation data available for this dataset",
                            x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
            plot_bgcolor='white', height=300
        )
        fig = go.FigureWidget(fig)
        return fig, pd.DataFrame(columns=["Affiliation", "Year", "Articles"])

    affiliations = [aff for sublist in AFF for aff in sublist]
    # Use only the PY values from the matching AFF index rows
    years = data.loc[AFF.index, "PY"].repeat(nAFF).values[:len(affiliations)]
    
    AFFY = pd.DataFrame({
        "Affiliation": affiliations,
        "Year": years
    })
    AFFY["Affiliation"] = AFFY["Affiliation"].apply(strip_accents).str.strip().str.upper()
    
    # Filter out non-reporting placeholder values to align with Most Relevant Affiliations
    invalid_vals = ["", "NA", "NAN", "NONE", "NOTREPORTED", "NOTDECLARED"]
    AFFY = AFFY[~AFFY["Affiliation"].isin(invalid_vals)].dropna(subset=["Affiliation", "Year"])

    if len(AFFY) == 0:
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text="No affiliation data available for this dataset",
                            x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
            plot_bgcolor='white', height=300
        )
        fig = go.FigureWidget(fig)
        return fig, pd.DataFrame(columns=["Affiliation", "Year", "Articles"])

    # Group by Affiliation and Year to calculate annual counts
    AFFY_grouped = AFFY.groupby(["Affiliation", "Year"]).size().reset_index(name="Articles")

    # Pivot to fill gaps in years with 0
    AFFY_pivot = AFFY_grouped.pivot(index="Affiliation", columns="Year", values="Articles").fillna(0)
    AFFY_stacked = AFFY_pivot.stack().reset_index(name="Articles")
    AFFY_stacked["Year"] = AFFY_stacked["Year"].astype(int)

    # Calculate Cumulative Sum of articles per affiliation over time
    AFFY_stacked = AFFY_stacked.sort_values(by=["Affiliation", "Year"])
    AFFY_stacked["Articles"] = AFFY_stacked.groupby("Affiliation")["Articles"].cumsum()

    # Select the top affiliations using the total cumulative sum in the final year (Most Relevant)
    final_year = AFFY_stacked["Year"].max()
    top_affs = AFFY_stacked[AFFY_stacked["Year"] == final_year].nlargest(top_k_affiliations, "Articles")["Affiliation"].tolist()
    
    AffOverTime = AFFY_stacked[AFFY_stacked["Affiliation"].isin(top_affs)]

    # CRITICAL FIX: Sort by BOTH Affiliation and Year chronologically to prevent Plotly line zig-zags!
    AffOverTime = AffOverTime.sort_values(by=["Affiliation", "Year"])

    # Convert Affiliation to Categorical to maintain ranking order in legend
    AffOverTime["Affiliation"] = pd.Categorical(
        AffOverTime["Affiliation"],
        categories=top_affs,
        ordered=True
    )
    AffOverTime = AffOverTime.sort_values(by=["Affiliation", "Year"])

    # Create the beautiful cumulative line chart with markers
    fig = px.line(
        AffOverTime,
        x="Year",
        y="Articles",
        color="Affiliation",
        markers=True,
        labels={"Year": "Year", "Articles": "Cumulative Articles", "Affiliation": "Affiliation"},
        template="simple_white",
    )

    # Customize layout with clean gridlines and legend
    unique_years = sorted(AffOverTime["Year"].unique())
    dtick = 1
    if len(unique_years) > 1:
        year_range = unique_years[-1] - unique_years[0]
        if year_range > 15:
            dtick = 2

    fig.update_layout(
        height=600,
        xaxis=dict(
            title="Year", 
            showgrid=True, 
            gridcolor="#EFEFEF",
            tickmode="linear",
            dtick=dtick
        ),
        yaxis=dict(
            title="Cumulative N. of Articles", 
            showgrid=True, 
            gridcolor="#EFEFEF",
            zeroline=False
        ),
        plot_bgcolor='white',
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(
            title="Affiliation",
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        )
    )

    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    # Sort final dataframe for clean return/display
    aff_top_out = AffOverTime.sort_values(by=["Year", "Affiliation"])

    return fig, aff_top_out
