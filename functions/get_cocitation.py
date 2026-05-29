from www.services import *


def get_co_citation(
    df, field, sep, cocit_network_layout, cocit_clustering_algorithm, cocit_repulsion,
    cocit_shape, cocit_shadow, cocit_curved, citlabelsize, citedgesize, citlabel_cex,
    citNodes, cit_isolates, citedges_min
):
    """
    Generate a co-citation network, similar to the R intellectualStructure function.

        Generates an interactive co-citation network visualization and related analytics, similar to the R intellectualStructure function.
    The function builds a co-citation network (references, authors, or sources), applies clustering, and visualizes the network
    with customizable layout, node/edge styles, and label handling. It also produces a density plot, a cluster summary table,
    and a degree plot for further analysis.
    Args:
        df (pd.DataFrame): Bibliographic data.
        field (str): Field for co-citation analysis ('CR', 'CR_AU', 'CR_SO').
        sep (str): Separator for references.
        cocit_network_layout (str): Network layout type (e.g., 'fr', 'kamada_kawai').
        cocit_clustering_algorithm (str): Clustering algorithm to use.
        cocit_repulsion (float): Repulsion force for community layout.
        cocit_shape (str): Node shape (e.g., 'dot', 'square').
        cocit_shadow (bool): Whether to display node shadow.
        cocit_curved (bool): Whether to use curved edges.
        citlabelsize (int): Maximum number of node labels to display.
        citedgesize (float): Edge size scaling factor.
        citlabel_cex (bool): Whether to scale label size.
        citNodes (int): Number of nodes to include in the network.
        cit_isolates (bool): Whether to remove isolated nodes.
        citedges_min (int): Minimum edge weight to display.
    Returns:
        html_filename (str): Filename of the generated HTML network visualization.
        fig_density (plotly.graph_objs.Figure): Density plot of node positions.
        cluster_table (pd.DataFrame): Table summarizing clusters and node centrality metrics.
        degree_plot (plotly.graph_objs.Figure): Degree distribution plot for network nodes.
    """

    M = df

    # Prepare network and title based on field
    NetRefs = None
    Title = ""
    if field == "CR":
        NetRefs = biblionetwork(M, analysis="co-citation", network="references", n=citNodes, sep=sep)
        Title = "Cited References network"
    elif field == "CR_AU":
        if "CR_AU" not in (M.get().columns if hasattr(M, 'get') else M.columns):
            M = metaTagExtraction(M, Field="CR_AU", sep=sep)
        NetRefs = biblionetwork(M, analysis="co-citation", network="authors", n=citNodes, sep=sep)
        Title = "Cited Authors network"
    elif field == "CR_SO":
        if "CR_SO" not in (M.get().columns if hasattr(M, 'get') else M.columns):
            M = metaTagExtraction(M, Field="CR_SO", sep=sep)
        NetRefs = biblionetwork(M, analysis="co-citation", network="sources", n=citNodes, sep=sep)
        Title = "Cited Sources network"

    if NetRefs is None or NetRefs.empty:
        raise ValueError("No citation relationships exist in this dataset. Please ensure your dataset contains 'Cited References' metadata (CR field) to perform Co-Citation Network analysis.")

    # Adjust number of labels if exceeds nodes
    label_n = min(citNodes, citlabelsize)

    # Prepare network plot
    cocitnet = network_plot(
        NetMatrix=NetRefs,
        normalize=None,
        Title=Title,
        type=cocit_network_layout,
        size_cex=True,
        size=5,
        remove_multiple=False,
        edgesize=citedgesize * 3,
        labelsize=citlabelsize,
        label_cex=citlabel_cex,
        curved=cocit_curved,
        label_n=label_n,
        edges_min=citedges_min,
        label_color=False,
        remove_isolates=cit_isolates,
        alpha=0.7,
        cluster=cocit_clustering_algorithm,
        community_repulsion=cocit_repulsion / 2,
        verbose=False
    )

    # Visualization (HTML, density plot, cluster table, degree plot)
    # The following is similar to get_co_occurence_network, but adapted for co-citation

    net = Network(height="98vh", width="100%", notebook=True, cdn_resources="in_line")
    net.toggle_physics(False)

    unique_clusters = set(cocitnet['cluster_obj'].membership)
    cluster_colors = {}
    for cluster_id in unique_clusters:
        r = np.random.randint(0, 255)
        g = np.random.randint(0, 255)
        b = np.random.randint(0, 255)
        cluster_colors[cluster_id] = f"rgba({r},{g},{b},0.7)"

    layout = cocitnet['graph']['layout']
    coords = np.array([[pos[0], pos[1]] for pos in layout])
    coords = coords / np.abs(coords).max()
    coords[:, 0] *= 1000
    coords[:, 1] *= 400

    node_labels = [v["name"] if "name" in v.attributes() else f"Node {v.index}" for v in cocitnet['graph'].vs]
    node_sizes = []
    nodes = []
    for idx, vertex in enumerate(cocitnet['graph'].vs):
        cluster_id = cocitnet['cluster_obj'].membership[vertex.index]
        node_color = cluster_colors[cluster_id]
        min_deg, max_deg = min(cocitnet['graph'].degree()), max(cocitnet['graph'].degree())
        node_size = 10 if max_deg == min_deg else (15 * (vertex.degree() - min_deg) / (max_deg - min_deg) + 10)
        node_size = max(10, min(130, node_size))
        font_size = node_size * 2
        node_sizes.append(node_size)
        min_font_size = 10
        max_font_size = 130
        font_opacity = np.sqrt((font_size - min_font_size) / (max_font_size - min_font_size)) * 0.7 + 0.3
        font_opacity = max(0.1, min(1, font_opacity))
        nodes.append({
            'id': vertex.index,
            'label': vertex["name"] if "name" in vertex.attributes() else f"Node {vertex.index}",
            'title': vertex["name"] if "name" in vertex.attributes() else f"Node {vertex.index}",
            'color': node_color,
            'size': node_size,
            'font': {
                'size': font_size,
                'color': f'rgba(0,0,0,{font_opacity})',
                'vadjust': -0.7 * font_size if cocit_shape.lower() in ['dot', 'square'] else 0
            },
            'shadow': cocit_shadow,
            'shape': cocit_shape,
            'x': layout[idx][0] * 1000,
            'y': layout[idx][1] * 1000
        })

    # Remove overlapping labels
    noOverlap = True
    if noOverlap:
        threshold = 0.05
        ymax = np.ptp(coords[:, 1])
        xmax = np.ptp(coords[:, 0])
        threshold2 = threshold * np.mean([xmax, ymax])
        labels_to_remove = avoid_net_overlaps(coords, node_labels, node_sizes, threshold=threshold2)
    else:
        labels_to_remove = []

    unique_nodes = {node['id']: node for node in nodes}.values()
    for node in unique_nodes:
        if node['label'] in labels_to_remove:
            node['label'] = ''
        net.add_node(node['id'], **node)

    added_edges = set()
    edge_weights = [e.attributes().get('weight', 1) for e in cocitnet['graph'].es]
    max_weight = max(edge_weights) if edge_weights else 1

    for edge in cocitnet['graph'].es:
        source, target = edge.tuple
        cluster_source = cocitnet['cluster_obj'].membership[source]
        cluster_target = cocitnet['cluster_obj'].membership[target]
        if cluster_source == cluster_target:
            base_color = cluster_colors[cluster_source]
            rgba_values = [int(x) for x in base_color[5:-1].split(',')[:-1]]
            edge_color = f"rgba({rgba_values[0]},{rgba_values[1]},{rgba_values[2]},0.56)"
        else:
            edge_color = "rgba(105,105,105,0.38)"
        edge_weight = edge.attributes().get('weight', 1)
        normalized_weight = (edge_weight ** 2 / (max_weight ** 2)) * (10 + 2.5)
        edge_tuple = (source, target) if source < target else (target, source)
        if edge_tuple not in added_edges:
            net.add_edge(
                source,
                target,
                color=edge_color,
                width=normalized_weight,
                smooth={'type': 'horizontal'} if cocit_curved else False,
                dashes=False
            )
            added_edges.add(edge_tuple)

    options_dict = {
        "nodes": {
            "shadow": bool(cocit_shadow)
        },
        "edges": {
            "smooth": {"type": "horizontal"} if cocit_curved else False
        },
        "interaction": {
            "dragNodes": True,
            "hideEdgesOnDrag": True,
            "navigationButtons": False,
            "zoomSpeed": 0.4
        },
        "physics": {
            "enabled": False
        },
        "manipulation": {
            "enabled": False
        }
    }
    net.set_options(json.dumps(options_dict))

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    html_path = tmp.name
    with open(html_path, 'w', encoding="utf-8") as f:
        html = net.generate_html()
        new_css = "     .card {\n                 border: none;\n             }"
        updated_html = html.replace("</style>", new_css + "\n        </style>")
        updated_html = updated_html.replace("1px solid lightgray", "none")
        
        f.write(updated_html)

    ##################################### Density Plot #####################################
    # Crea il dataframe originale e correggi le coordinate y
    nodes_df_orig = pd.DataFrame(nodes)
    nodes_df_orig['y'] = nodes_df_orig['y'] * -1

    # Calcola la dimensione del font seguendo la formula: (((font.size - min(font.size)) / diff(range(font.size)))*20)+10
    font_sizes = nodes_df_orig['font'].apply(lambda x: x.get('size', 75))
    min_font = font_sizes.min()
    max_font = font_sizes.max()
    nodes_df_orig['font_size'] = ((font_sizes - min_font) / (max_font - min_font) * 20) + 10 if max_font > min_font else 15

    # Crea il dataframe replicato per il density plot:
    nodes_df = nodes_df_orig.copy()
    nodes_df['log'] = np.ceil(np.log(nodes_df['size']))
    nodes_df = nodes_df.loc[nodes_df.index.repeat(nodes_df['log'].astype(int))]

    # Definisci la colorscale "Reds" con transizioni armoniose
    reds_colors = [
        [0.0, 'rgb(255,255,255)'],
        [0.05, 'rgb(238,238,238)'],
        [0.125, 'rgb(254,224,210)'],
        [0.25, 'rgb(252,187,161)'],
        [0.375, 'rgb(252,146,114)'],
        [0.5, 'rgb(251,106,74)'],
        [0.625, 'rgb(239,59,44)'],
        [0.75, 'rgb(203,24,29)'],
        [0.875, 'rgb(165,15,21)'],
        [1.0, 'rgb(103,0,13)']
    ]

    # Crea il grafico 2D histogram
    fig_density = go.Figure()
    fig_density.add_trace(go.Histogram2d(
        x=nodes_df['x'],
        y=nodes_df['y'],
        histnorm='density',
        colorscale=reds_colors,
        showscale=False,
        zsmooth='best'
    ))

    # Aggiungi le annotazioni (usando i dati originali)
    for _, row in nodes_df_orig.iterrows():
        fig_density.add_annotation(
            xref='x1',
            yref='y',
            x=row['x'],
            y=row['y'],
            text=row['label'],
            showarrow=False,
            font=dict(
                family='Arial',
                size=row['font_size'],
                color='black'
            )
        )

    # Update layout to match R implementation
    fig_density.update_layout(
        xaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            showline=False,
            showticklabels=False,
            domain=[0, 1],
            gridcolor='#FFFFFF',
            tickvals=[]
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            zeroline=False,
            showline=False,
            showticklabels=False, 
            domain=[0, 1],
            gridcolor='#FFFFFF',
            tickvals=[]
        ),
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        showlegend=False,
        hovermode=False
    )

    # Remove hover info
    fig_density.update_traces(hoverinfo='none')

    fig_density.update_layout(
        height=750,
        autosize=True,
        width=None,
        showlegend=True,
        margin=dict(t=20)  # aggiunge spazio bianco sopra
    )
    fig_density = go.FigureWidget(fig_density)
    fig_density._config = fig_density._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    # Cluster results table
    cluster_data = pd.DataFrame({
        'Node': [v['name'] if 'name' in v.attributes() else f'Node {v.index}' for v in cocitnet['graph'].vs],
        'Cluster': cocitnet['cluster_obj'].membership,
        'Betweenness': cocitnet['graph'].betweenness(),
        'Closeness': cocitnet['graph'].closeness(),
        'PageRank': cocitnet['graph'].pagerank()
    })
    numeric_cols = ['Betweenness', 'Closeness', 'PageRank']
    cluster_data[numeric_cols] = cluster_data[numeric_cols].round(3)
    cocitnet['cluster_res'] = cluster_data

    # Degree plot
    node_degrees = pd.DataFrame({
        'node': [v['name'] if 'name' in v.attributes() else f'Node {v.index}' for v in cocitnet['graph'].vs],
        'degree': cocitnet['graph'].degree()
    })
    node_degrees = node_degrees.sort_values('degree', ascending=False)
    node_degrees['x'] = range(1, len(node_degrees) + 1)
    max_degree = node_degrees['degree'].max()
    node_degrees['degree'] = node_degrees['degree'] / max_degree if max_degree > 0 else node_degrees['degree']

    degree_plot = go.Figure()
    degree_plot.add_trace(go.Scatter(
        x=node_degrees['x'],
        y=node_degrees['degree'],
        mode='lines+markers',
        line=dict(color='#5567BB', width=1),
        marker=dict(size=6),
        hovertemplate='%{text}<extra></extra>',
        text=[f"{node} - Degree {degree:.3f}" for node, degree in zip(node_degrees['node'], node_degrees['degree'])]
    ))
    degree_plot.update_layout(
        xaxis_title='Node',
        yaxis_title='Cumulative Degree',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='#444444'),
        title_font_size=24,
        xaxis=dict(
            showgrid=True,
            gridcolor='#EFEFEF',
            title_font=dict(size=14, color='#5567BB'),
            showline=True,
            linewidth=0.5,
            linecolor='black'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#EFEFEF',
            title_font=dict(size=14, color='#5567BB'),
            title_standoff=25,
            showline=True,
            linewidth=0.5,
            linecolor='black'
        )
    )

    # Personalizza l'hovertemplate per renderlo leggibile e carino
    degree_plot.update_traces(
        hovertemplate=(
            "<b>Node:</b> %{text}<br>"
            "<b>Rank:</b> %{x}<br>"
            "<b>Normalized Degree:</b> %{y:.3f}<extra></extra>"
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),
    )

    # Remove hover info
    degree_plot.update_layout(
        height=750,
        autosize=True,
        width=None,
        showlegend=True,
        margin=dict(t=20)  # aggiunge spazio bianco sopra
    )
    degree_plot = go.FigureWidget(degree_plot)
    degree_plot._config = degree_plot._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return html_path.split(os.sep)[-1], fig_density, cocitnet['cluster_res'], degree_plot, 
