from www.services import *


def get_author_production_over_time(df, top_k_authors):
    """
    Generates a scatter plot showing authors' production over time with point sizes representing their production, 
    including lines connecting points. Also calculates total citations (TC) and total citations per year (TCpY).

    Args:
        df (pd.DataFrame): Dataset containing columns "AU" (authors), "PY" (year), "TI" (title), 
                           "SO" (source), "DOI" (DOI), and "TC" (total citations).
        top_k_authors (int): Number of top authors to display.

    Returns:
        fig: Plotly figure.
        table_authors_production (pd.DataFrame): Table summarizing authors' production with TC and TCpY.
        table_documents (pd.DataFrame): Detailed table with additional document information.
    """
    data = df.get()

    # Ensure "PY" is numeric and valid (ignore years <= 1800)
    data["PY"] = pd.to_numeric(data["PY"], errors="coerce")
    data = data[data["PY"] > 1800]

    # Remove rows with invalid "PY" or "AU" values
    data = data.dropna(subset=["PY", "AU"])

    # Ensure "AU" is a list and split author names
    data["AU"] = data["AU"].apply(lambda x: x if isinstance(x, list) else str(x).split(","))
    data = data.explode("AU")
    data["AU"] = data["AU"].str.strip()  # Remove leading and trailing spaces
    data["AU"] = data["AU"].str.replace(r"\[|\]", "", regex=True)  # Remove unwanted characters

    # Remove rows with missing or empty author names
    data = data.dropna(subset=["AU"])
    data = data[data["AU"] != ""]

    # Check and clean "TC" column
    if "TC" in data.columns:
        data["TC"] = pd.to_numeric(data["TC"], errors="coerce").fillna(0)
    else:
        print("Warning: 'TC' column is missing! Defaulting to 0.")
        data["TC"] = 0

    # Calculate production per author and year
    author_production = (
        data.groupby(["AU", "PY"])
        .agg(Production=("AU", "size"), TotalCitations=("TC", "sum"))
        .reset_index()
    )

    # Calculate TCpY (Total Citations Per Year)
    current_year = pd.Timestamp.now().year
    author_production["TCpY"] = author_production.apply(
        lambda row: row["TotalCitations"] if row["PY"] >= current_year 
        else row["TotalCitations"] / (current_year - row["PY"] + 1),
        axis=1
    )

    # Filter top_k_authors
    top_authors = (
        author_production.groupby("AU")["Production"]
        .sum()
        .nlargest(top_k_authors)
        .index
    )
    author_production = author_production[author_production["AU"].isin(top_authors)]

    # Create scatter plot
    fig = px.scatter(
        author_production,
        x="PY",
        y="AU",
        size="Production",
        color="AU",
        labels={
            "PY": "Year", 
            "AU": "Author", 
            "Production": "Number of Publications",
            "TotalCitations": "Total Citations",
            "TCpY": "Citations Per Year"
        },
        template="simple_white",
    )

    # Add lines connecting points
    for author in top_authors:
        author_data = author_production[author_production["AU"] == author]
        fig.add_trace(
            go.Scatter(
                x=author_data["PY"],
                y=author_data["AU"],
                mode="lines",
                line=dict(color="lightgray", width=3),
                name=f"{author} (trend)",
                showlegend=False  # Hide trend lines from the legend
            )
        )

    # Customize layout
    fig.update_traces(marker=dict(opacity=0.7, line=dict(width=0.5, color="DarkSlateGrey")))
    fig.update_layout(
        height=800,  # Chart height
        xaxis=dict(title="Year", showgrid=True, gridcolor="lightgrey", dtick=2),
        yaxis=dict(
            title="Author", 
            showgrid=True, 
            gridcolor="lightgrey",
            categoryorder="array",
            categoryarray=list(top_authors)[::-1]
        ),
        showlegend=False,
        margin=dict(l=0, r=0, t=40, b=0),  # Margins
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    # Sort production table by year and author
    table_authors_production = author_production.sort_values(by=["PY", "AU"])[["AU", "PY", "Production", "TotalCitations", "TCpY"]]

    # Create a detailed table for documents
    required_columns = ["AU", "PY", "TI", "SO", "DI", "TC"]
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        print(f"Warning: Missing columns in data: {missing_columns}")
        table_documents = pd.DataFrame()  # Empty DataFrame if required columns are missing
    else:
        # Calculate TCpY for each document
        data["TCpY"] = data.apply(
            lambda row: row["TC"] if row["PY"] >= current_year 
            else row["TC"] / (current_year - row["PY"] + 1),
            axis=1
        )
        table_documents = data[required_columns + ["TCpY"]]
        # Filter documents to include only authors present in author_production
        table_documents = table_documents[table_documents["AU"].isin(author_production["AU"].unique())].sort_values(by=["PY", "AU"])

    return fig, table_authors_production, table_documents
