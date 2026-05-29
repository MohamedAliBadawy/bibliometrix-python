from www.services import *
import textwrap


def get_three_field_plot(df, left_field, middle_field, right_field, left_field_items, middle_field_items, right_field_items):
    """
    Generate a three-field plot (Sankey diagram) to visualize the main items of three fields and their relationships.

    Args:
        df: A DataFrame object containing the data.
        left_field: The field for the left side of the plot.
        middle_field: The field for the middle of the plot.
        right_field: The field for the right side of the plot.
        left_field_items: Number of items to plot for the left field.
        middle_field_items: Number of items to plot for the middle field.
        right_field_items: Number of items to plot for the right field.
        
    Returns:
        A Plotly figure object representing the three-field plot.
    """
    fields = [left_field, middle_field, right_field]
    n = [left_field_items, middle_field_items, right_field_items]

    if "CR_SO" in fields:
        df = metaTagExtraction(df, "CR_SO")
    if "AU_CO" in fields:
        df = metaTagExtraction(df, "AU_CO")
    if "AB_TM" in fields:
        df = term_extraction(df, field="AB")
    if "TI_TM" in fields:
        df = term_extraction(df, field="TI")

    # Document x Attribute matrix Field LEFT
    WL = cocMatrix(df, fields[0], binary=True, n=n[0])
    if WL is None or WL.shape[1] == 0:
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text=f"No data available for field '{fields[0]}'",
                            x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
            plot_bgcolor='white', height=300
        )
        return go.FigureWidget(fig)
    n1 = min(n[0], WL.shape[1])
    TopL = WL.columns.tolist()

    # Document x Attribute matrix Field MIDDLE
    WM = cocMatrix(df, fields[1], binary=True, n=n[1])
    if WM is None or WM.shape[1] == 0:
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text=f"No data available for field '{fields[1]}'",
                            x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
            plot_bgcolor='white', height=300
        )
        return go.FigureWidget(fig)
    n2 = min(n[1], WM.shape[1])
    TopM = WM.columns.tolist()

    # Document x Attribute matrix Field RIGHT
    WR = cocMatrix(df, fields[2], binary=True, n=n[2])
    if WR is None or WR.shape[1] == 0:
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text=f"No data available for field '{fields[2]}'",
                            x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
            plot_bgcolor='white', height=300
        )
        return go.FigureWidget(fig)
    n3 = min(n[2], WR.shape[1])
    TopR = WR.columns.tolist()

    # Co-Occurrence Matrices
    LM = WL.T.dot(WM)
    MR = WM.T.dot(WR)

    LM.index = range(1, n1 + 1)
    LM.columns = range(n1 + 1, n1 + n2 + 1)
    MR.index = range(n1 + 1, n1 + n2 + 1)
    MR.columns = range(n1 + n2 + 1, n1 + n2 + n3 + 1)

    # Melting matrices to get edges
    def melt_matrix(matrix):
        var1 = np.repeat(matrix.index.values, matrix.shape[1])
        var2 = np.tile(matrix.columns.values, matrix.shape[0])
        values = matrix.values.flatten()
        melted_df = pd.DataFrame({'Var1': var1, 'Var2': var2, 'Value': values})
        return melted_df

    LMm = melt_matrix(LM)
    LMm["group"] = None
    MRm = melt_matrix(MR)
    MRm["group"] = None

    # Concatenate edge data
    Edges = pd.concat([LMm, MRm], ignore_index=True)
    Edges['Var1'] = Edges['Var1'].astype(int)
    Edges['Var2'] = Edges['Var2'].astype(int)
    Edges.columns = ["from", "to", "Value", "group"]
    Edges = Edges.dropna(subset=['to', 'from'])
    Edges['from'] = Edges['from'] - 1  # Make indices 0-based
    Edges['to'] = Edges['to'] - 1
    Edges = Edges.drop(columns=['group'])
    Edges = Edges[Edges["Value"] >= 1]  # Filter edges with weight >= min.flow

    # Same as before up to where Nodes are created
    Nodes = pd.DataFrame({
        "Nodes": [*TopL, *TopM, *TopR],
        "group": [fields[0]] * len(TopL) + [fields[1]] * len(TopM) + [fields[2]] * len(TopR),
        "level": [1] * len(TopL) + [2] * len(TopM) + [3] * len(TopR)
    })
    Nodes["id"] = range(len(Nodes))
    min_flow = 1
    Edges.rename(columns={"Value": "weight"}, inplace=True)
    Edges = Edges[Edges["weight"] >= min_flow]

    # Set x positions for nodes based on level
    Kx = len(Nodes['group'].unique())
    Ky = len(Nodes)
    Nodes['coordX'] = np.repeat(np.linspace(0, 1, Kx), Nodes['level'].value_counts().sort_index().values)
    Nodes['coordY'] = np.repeat(0.1, Ky)

    # Set custom base colors for nodes by group for better distinction
    group_colors = {
        fields[0]: "#3288BD",  # Blue
        fields[1]: "#F46D43",  # Orange
        fields[2]: "#66C2A5",  # Green
    }

    # Calculate node weights (sum of incoming and outgoing edge weights)
    node_weights = pd.concat([
        Edges.groupby('from')['weight'].sum(),
        Edges.groupby('to')['weight'].sum()
    ], axis=1).fillna(0).sum(axis=1)
    Nodes['weight'] = Nodes['id'].map(node_weights).fillna(0)

    # Function to add opacity to a hex color based on node weight (higher weight = less transparent)
    def hex_to_rgba(hex_color, opacity):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return f'rgba({rgb[0]},{rgb[1]},{rgb[2]},{opacity:.2f})'

    # Normalize weights to [0.3, 1.0] for opacity (avoid fully transparent nodes)
    min_opacity, max_opacity = 0.3, 1.0
    if Nodes['weight'].max() > 0:
        norm_weights = (Nodes['weight'] - Nodes['weight'].min()) / (Nodes['weight'].max() - Nodes['weight'].min())
        opacities = norm_weights * (max_opacity - min_opacity) + min_opacity
    else:
        opacities = np.full(len(Nodes), min_opacity)

    Nodes['color'] = [
        hex_to_rgba(group_colors[g], o)
        for g, o in zip(Nodes['group'], opacities)
    ]

    # Shorten long labels and add line breaks for better visibility
    def wrap_label(label, width=45):
        return "<br>".join(textwrap.wrap(str(label), width=width))

    Nodes['wrapped_label'] = Nodes['Nodes'].apply(lambda x: wrap_label(x, width=35))

    # Identify and remove nodes with empty edges
    ind = set(Nodes['id']) - set(Edges['from']).union(set(Edges['to']))
    if ind:
        Nodes = Nodes[~Nodes['id'].isin(ind)]
        Nodes['idnew'] = range(len(Nodes))
        id_map = dict(zip(Nodes['id'], Nodes['idnew']))
        Edges['from'] = Edges['from'].map(id_map)
        Edges['to'] = Edges['to'].map(id_map)
        Nodes['id'] = Nodes['idnew']

    # Create figure
    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=28,
            line=dict(color="black", width=1),
            label=Nodes["wrapped_label"],
            color=Nodes["color"],
            x=Nodes["coordX"],
            y=Nodes["coordY"],
            customdata=Nodes["Nodes"],
            hovertemplate='%{customdata}<extra></extra>',
        ),
        link=dict(
            source=Edges["from"],
            target=Edges["to"],
            value=Edges["weight"],
            color="rgba(120,120,120,0.25)",
            hovertemplate='From: %{source.label}<br>To: %{target.label}<br>Value: %{value}<extra></extra>',
        )
    )])

    # Add group annotations at the top of each column
    for level, field in enumerate(fields, start=1):
        group_nodes = Nodes[Nodes['level'] == level]
        if not group_nodes.empty:
            x_pos = group_nodes['coordX'].mean()
            fig.add_annotation(
                x=x_pos,
                y=1.13,
                text=f"<b>{wrap_label(field, width=18)}</b>",
                showarrow=False,
                xanchor='center',
                font=dict(color=group_colors[field], family="Arial", size=15)  # Font size 
            )

    # Update layout for aesthetics and readability
    fig.update_layout(
        font=dict(size=11, color='Black'),  # Font size
        margin=dict(l=80, r=80, b=50, t=120, pad=4),
        height=820,
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {
        'modeBarButtonsToRemove': [
            'sendDataToCloud', 'pan', 'select', 'lasso2d', 'toImage',
            'toggleSpikelines', 'hoverClosestCartesian', 'hoverCompareCartesian'
        ],
        'displaylogo': False
    }

    return fig
