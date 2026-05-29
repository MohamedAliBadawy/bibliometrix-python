from www.services import *


def get_cited_documents(df, num_of_cited_docs, cited_docs_measure):
    """
    Generate a plot and table of the most cited documents.
    
    Args:
        df: A DataFrame object containing the data.
        num_of_cited_docs: The number of top cited documents to display.
        cited_docs_measure: The measure to use for ranking (either "TC" for total citations or "TCperYear" for citations per year).
        
    Returns:
        A Plotly figure object and a DataFrame of the most cited documents.
    """
    # Extract metadata tags for cited documents
    df = metaTagExtraction(df, "SR")
    df = df.get()

    # Prepare the table for ranking documents
    current_year = pd.to_datetime("today").year
    df["TCperYear"] = df["TC"] / (current_year + 1 - df["PY"])
    
    # Calculate NormalizedTC within each publication year
    df["NormalizedTC"] = df.groupby("PY")["TC"].transform(lambda x: x / x.mean()).round(2)
    
    tab = (
        df.reset_index(drop=True).dropna(subset=["SR"])
        .groupby("SR", as_index=False)
        .agg(DI=("DI", "first"), TotalCitation=("TC", "sum"), TCperYear=("TCperYear", lambda x: round(x.sum(), 1)), NormalizedTC=("NormalizedTC", "sum"))
        .rename(columns={"SR": "Document"})
        .sort_values(by="TotalCitation", ascending=False)
    )

    # Convert columns to numeric to ensure correct calculations
    tab["TotalCitation"] = pd.to_numeric(tab["TotalCitation"])
    tab["TCperYear"] = pd.to_numeric(tab["TCperYear"])
    tab["NormalizedTC"] = pd.to_numeric(tab["NormalizedTC"])
    tab = tab.sort_values(by="TotalCitation", ascending=False)
    table = tab
    tab = tab.head(num_of_cited_docs)

    # Select the appropriate measure based on user input
    if cited_docs_measure == "total_cit":
        tab = tab[["Document", "TotalCitation", "NormalizedTC"]]
        laby = "Global Citations"
    else:
        tab = tab.sort_values(by="TCperYear", ascending=False)[["Document", "TCperYear", "NormalizedTC"]]
        laby = "Global Citations per Year"

    # Create the plot (horizontal scatter with lines, similar to author plot)
    fig = go.Figure()

    # Prepare y-ticks and labels
    y_labels = tab["Document"]
    y_vals = list(range(len(tab)))

    # Add a thick line from each label to its marker
    for i, row in enumerate(tab.itertuples()):
        fig.add_shape(
            type="line",
            x0=0,
            x1=getattr(row, tab.columns[1]),
            y0=i,
            y1=i,
            line=dict(color="#e0e0e0", width=5),
            layer="below",
        )

    # Add scatter markers and text
    fig.add_trace(
        go.Scatter(
            x=tab[tab.columns[1]],
            y=y_vals,
            mode="markers+text",
            marker=dict(
                size=18 + 6 * (tab[tab.columns[1]] / max(tab[tab.columns[1]].max(), 1)),
                color=tab[tab.columns[1]],
                colorscale=[[0, "#B3D1F2"], [1, "#5567BB"]],
                line=dict(width=1, color="#E0E0E0"),
                opacity=0.95,
                showscale=False,
            ),
            text=tab[tab.columns[1]],
            textposition="top center",
            textfont=dict(color="#5567BB", size=13),
            hovertemplate=(
                "<b>Document:</b> %{customdata}<br>"
                "<b>" + laby + ":</b> %{x}<extra></extra>"
            ),
            customdata=tab["Document"],
        )
    )

    # Add horizontal grid lines for each document (lighter)
    for i in range(len(tab)):
        fig.add_shape(
            type="line",
            x0=0,
            x1=tab[tab.columns[1]].max(),
            y0=i,
            y1=i,
            line=dict(color="#E0E0E0", width=2),
            layer="below",
        )

    # Set x-axis ticks
    max_x = tab[tab.columns[1]].max()
    tick_step = max(1, int(max_x // 6))
    x_ticks = list(range(0, int(max_x) + tick_step, tick_step))
    if x_ticks[-1] < max_x:
        x_ticks.append(int(max_x))

    fig.update_yaxes(
        tickvals=y_vals,
        ticktext=y_labels,
        autorange="reversed",
        showgrid=False,
        title="Document",
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
        height=50 + 90 * len(tab),
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
