from www.services import *


def get_thematic_evolution(df, field="ID", years=None, n=250, weight_index="inc_index", min_weight_index=0.1, minFreq=2,
                           size=0.5, ngrams=1, stemming=False, n_labels=1, repel=True, remove_terms=None, synonyms=None, cluster="walktrap"):
    """
    Function to perform thematic evolution analysis on a bibliographic DataFrame.

    Args:
        df (pd.DataFrame): Bibliographic DataFrame with a 'PY' (Publication Year) column.
        field (str): Field to analyze. Can be "ID", "DE", "TI", or "AB".
        years (list): List of years to split the data.
        n (int): Maximum number of terms to consider.
        weight_index (str): Weight index for measuring flows ("Inclusion", "Inc_Weighted", "Stability").
        min_weight_index (float): Minimum threshold for the flow.
        minFreq (int): Minimum frequency of terms.
        size (float): Node size in the graph.
        ngrams (int): Size of n-grams.
        stemming (bool): If True, applies stemming to terms.
        n_labels (int): Number of labels to display.
        repel (bool): If True, applies repulsion to avoid node overlap.
        remove_terms (list): List of terms to remove from the analysis.
        synonyms (dict): Dictionary of synonyms to consider in the analysis.
        cluster (str): Clustering algorithm to use.

    Returns:
        dict: Results of the thematic evolution analysis.
    """
    results = thematic_evolution(
        M=df,
        field=field,
        years=years,
        n=n,
        min_freq=minFreq,
        size=size,
        ngrams=ngrams,
        stemming=stemming,
        n_labels=n_labels,
        repel=repel,
        remove_terms=remove_terms,
        synonyms=synonyms,
        cluster=cluster
    )

    ############################### PLOT THEMATIC EVOLUTION ###############################
    nodes = results['Nodes']
    edges = results['Edges']
    label_size = int(size * 20)

    net = plot_thematic_evolution(
        Nodes=nodes,
        Edges=edges,
        measure=weight_index,
        min_flow=min_weight_index,
        label_size=label_size
    )

    # Save network to HTML
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    html_path = tmp.name
    with open(html_path, 'w', encoding="utf-8") as f:
        html = net.generate_html()
        new_css = "     .card {\n                 border: none;\n             }"
        updated_html = html.replace("</style>", new_css + "\n        </style>")
        updated_html = updated_html.replace("1px solid lightgray", "none")
        
        f.write(updated_html)

    ########## Thematic Evalution Table ##########    
    # Prepara la tabella di evoluzione tematica
    thematic_table = results["Data"].copy()
    thematic_table = thematic_table.rename(columns={
        "Cluster_Label.x": "From",
        "Cluster_Label.y": "To",
        "Words": "Words",
        "Inc_Weighted": "Weighted Inclusion Index",
        "Inc_index": "Inclusion Index",
        "Occ": "Occurrences",
        "Stability": "Stability Index"
    })[
        ["From", "To", "Words", "Weighted Inclusion Index", "Inclusion Index", "Occurrences", "Stability Index"]
    ]

    return html_path.split(os.sep)[-1], thematic_table, results["TM"]


def thematic_evolution(M, field="ID", years=None, n=250, min_freq=2, size=0.5, ngrams=1, stemming=False, n_labels=1, repel=True, remove_terms=None, synonyms=None, cluster="walktrap"):
    if years is None:
        raise ValueError("You must provide a list of years for thematic evolution analysis.")
    
    list_df = timeslice(M, breaks=years)
    net, res = [], []
    Y = []

    for interval_label, Mk in list_df.items():
        Y.append(f"{min(Mk['PY'])}-{max(Mk['PY'])}")
        Mk = reactive.Value(Mk)
        resk_tuple = thematic_map(
            Mk,
            field=field, n=n, minfreq=min_freq, ngrams=ngrams,
            stemming=stemming, size=size, n_labels=n_labels,
            repel=repel, remove_terms=remove_terms, synonyms=synonyms, cluster=cluster, subgraphs=False
        )
        
        if resk_tuple is None:
            raise ValueError(f"For the period '{interval_label}', either the network co-occurrence matrix is empty or no keywords met the minimum frequency threshold. Please try lowering the minimum frequency (minFreq) or using a different year partition.")
            
        # thematic_map returns a tuple, so convert to dict for compatibility
        resk = {
            'map': resk_tuple[0],
            'net_html': resk_tuple[1],
            'words': resk_tuple[2],
            'clusters': resk_tuple[3],
            'documentToClusters': resk_tuple[4],
            'nclust': resk_tuple[5]['nclust'] if len(resk_tuple) > 5 and isinstance(resk_tuple[5], dict) and 'nclust' in resk_tuple[5] else len(resk_tuple[3]) if len(resk_tuple) > 3 and resk_tuple[3] is not None else 0,
            'net': resk_tuple[5]['net'] if len(resk_tuple) > 5 and isinstance(resk_tuple[5], dict) and 'net' in resk_tuple[5] else None,
            'subgraphs': resk_tuple[5]['subgraphs'] if len(resk_tuple) > 5 and isinstance(resk_tuple[5], dict) and 'subgraphs' in resk_tuple[5] else None,
            'params': resk_tuple[5]['params'] if len(resk_tuple) > 5 and isinstance(resk_tuple[5], dict) and 'params' in resk_tuple[5] else None,
        }
        # If the tuple is actually the results dict, just use it directly
        if isinstance(resk_tuple, dict):
            resk = resk_tuple
        # Only filter 'params' if it exists and is a DataFrame
        if 'params' in resk and isinstance(resk['params'], pd.DataFrame):
            resk['params'] = resk['params'][resk['params']['params'] != "minfreq"]
        res.append(resk)
        net.append(resk['net_html'])
    
    K = len(list_df)

    if K < 2:
        py_clean = pd.to_numeric(M.get()['PY'], errors='coerce').dropna()
        min_py = int(py_clean.min()) if not py_clean.empty else "N/A"
        max_py = int(py_clean.max()) if not py_clean.empty else "N/A"
        raise ValueError(f"Thematic Evolution requires at least 2 time periods. Please adjust your breakpoints to partition your dataset (publication years in dataset: {min_py} to {max_py}).")
    
    inc_matrix = []
    for k in range(1, K):
        res1 = res[k - 1]
        res2 = res[k]

        if res1['nclust'] == 0 or res2['nclust'] == 0:
            print(f"\nNo topics in the period {k - 1} with this set of input parameters\n\n")
            return {"check": False}

        # Ensure we do not append the period label multiple times
        def append_period(label, period):
            label = str(label)
            # Remove any trailing '--<period>' if already present
            if label.endswith(f"--{period}"):
                return label
            # Remove any repeated period labels (e.g., --2016-2017--2016-2017)
            parts = label.split('--')
            if len(parts) > 1 and parts[-1] == period:
                label = '--'.join(parts[:-1])
            return f"{label}--{period}"

        res1['words']['Cluster_Label'] = res1['words']['Cluster_Label'].apply(lambda x: append_period(x, Y[k - 1]))
        res1['clusters']['label'] = res1['clusters']['Cluster'].apply(lambda x: append_period(x, Y[k - 1]))

        res2['words']['Cluster_Label'] = res2['words']['Cluster_Label'].apply(lambda x: append_period(x, Y[k]))
        res2['clusters']['label'] = res2['clusters']['Cluster'].apply(lambda x: append_period(x, Y[k]))

        # Step 1: Add len and tot columns to clusters
        cluster1 = res1['words'].groupby('Cluster_Label').apply(lambda x: x.assign(
            len=len(x), tot=x['Occurrences'].sum()
        )).reset_index(drop=True)
        cluster2 = res2['words'].groupby('Cluster_Label').apply(lambda x: x.assign(
            len=len(x), tot=x['Occurrences'].sum()
        )).reset_index(drop=True)

        # Step 2: Inner join on Words
        A = pd.merge(cluster1, cluster2, on="Words", suffixes=(".x", ".y"))

        # Step 3: For each pair of clusters, compute min, Occ, tot
        A['min'] = A[['Occurrences.x', 'Occurrences.y']].min(axis=1)
        A['Occ'] = A['Occurrences.x']
        A['tot'] = A[['tot.x', 'tot.y']].min(axis=1)

        # Step 4: Group and summarize as in R
        B = (
            A.groupby(['Cluster_Label.x', 'Cluster_Label.y'])
            .apply(lambda row: pd.Series({
            "CL1": row['Cluster.x'].iloc[0],
            "CL2": row['Cluster.y'].iloc[0],
            "Words": ";".join(row['Words']),
            "sum": row['min'].sum(),
            "Inc_Weighted": row['min'].sum() / row['tot'].min() if row['tot'].min() > 0 else 0,
            "Inc_index": len(row['Words']) / min(row['len.x'].iloc[0], row['len.y'].iloc[0]) if min(row['len.x'].iloc[0], row['len.y'].iloc[0]) > 0 else 0,
            "Occ": row['Occ'].iloc[0],
            "Tot": row['tot'].iloc[0],
            "Stability": len(row['Words']) / (row['len.x'].iloc[0] + row['len.y'].iloc[0] - len(row['Words'])) if (row['len.x'].iloc[0] + row['len.y'].iloc[0] - len(row['Words'])) > 0 else 0
            }))
            .reset_index()
        )

        inc_matrix.append(B)

        if not inc_matrix:
            print("Error: No inclusion matrix was created.")
            return None

        # Concatenate all inclusion matrices
        INC = pd.concat(inc_matrix, ignore_index=True)

        # Edges dataframe
        edges = INC[['Cluster_Label.x', 'Cluster_Label.y', 'Inc_index', 'Inc_Weighted', 'Stability']].copy()

        # Nodes dataframe
        unique_labels = pd.unique(edges[['Cluster_Label.x', 'Cluster_Label.y']].values.ravel())
        nodes = pd.DataFrame({'name': unique_labels})
        nodes['group'] = nodes['name']

        # Assign numeric IDs to nodes
        nodes = nodes.reset_index(drop=True)
        nodes['id'] = nodes.index

        # Map cluster labels to node IDs for 'from' and 'to'
        label_to_id = dict(zip(nodes['name'], nodes['id']))
        edges['from'] = edges['Cluster_Label.x'].map(label_to_id)
        edges['to'] = edges['Cluster_Label.y'].map(label_to_id)

        # Rename columns as in R
        edges = edges.rename(columns={
            "Cluster_Label.x": "from_label",
            "Cluster_Label.y": "to_label",
            "Inc_index": "Inclusion",
            "Inc_Weighted": "Inc_Weighted",
            "Stability": "Stability"
            })
        edges['from'] = edges['from'].astype(int)
        edges['to'] = edges['to'].astype(int)

        # For colors and slices
        # nodes: separate name and group by '--', and assign slice as factor 1:K
        nodes = nodes.copy()
        nodes['name'] = nodes['name'].astype(str)
        split_cols = nodes['name'].str.split('--', n=1, expand=True)
        split_cols = split_cols.reindex(columns=[0, 1], fill_value='')
        nodes['name'] = split_cols[0]
        nodes['group'] = split_cols[1]
        nodes['slice'] = nodes['group'].apply(lambda x: Y.index(x) + 1 if x in Y else 1)
        nodes['label'] = nodes['name'] + '--' + nodes['group']

        Nodes = pd.DataFrame()
        for i in range(1, K + 1):
            nodes_i = nodes[nodes['slice'] == i].copy()
            clusters_df = res[i - 1]['clusters']
            color_col = 'color' if 'color' in clusters_df.columns else None
            name_col = 'name' if 'name' in clusters_df.columns else (
                'Cluster_Label' if 'Cluster_Label' in clusters_df.columns else None
            )
            if color_col and name_col:
                clusters_df = clusters_df[[color_col, name_col]].copy()
                clusters_df = clusters_df.rename(columns={name_col: 'name'})
            else:
                if not color_col:
                    clusters_df['color'] = "#D3D3D3"
                if not name_col:
                    clusters_df['name'] = clusters_df.index.astype(str)
                clusters_df = clusters_df[['color', 'name']].copy()
            merged = nodes_i.merge(clusters_df, left_on='name', right_on='name', how='left')
            Nodes = pd.concat([Nodes, merged], ignore_index=True)

        # Add 'sum' column: for each label, get max sum from both CL1 and CL2
        sums_CL1 = INC[['CL1', 'sum']].rename(columns={'CL1': 'label'})
        sums_CL2 = INC[['CL2', 'sum']].rename(columns={'CL2': 'label'})
        sums = pd.concat([sums_CL1, sums_CL2], ignore_index=True)
        sums['label'] = sums['label'].astype(str)
        Nodes['label'] = Nodes['label'].astype(str)
        sums = sums.groupby('label', as_index=False)['sum'].max()
        Nodes = Nodes.merge(sums, left_on='label', right_on='label', how='left')

        # Normalize sum within each slice, avoid division by zero
        Nodes['sum'] = Nodes.groupby('slice')['sum'].transform(lambda x: x / x.sum() if x.sum() > 0 else 0)

    # Prepare params as DataFrame
    params = {
        "field": field,
        "years": years,
        "n": n,
        "minFreq": min_freq,
        "size": size,
        "ngrams": ngrams,
        "stemming": stemming,
        "n_labels": n_labels,
        "repel": repel,
        "remove_terms": remove_terms,
        "synonyms": synonyms,
        "cluster": cluster
    }

    params_df = pd.DataFrame(list(params.items()), columns=['params', 'values'])
    results = {
        "Nodes": Nodes,
        "Edges": edges,
        "Data": INC,
        "check": True,
        "TM": res,
        "Net": net,
        "params": params_df
    }
    
    return results


def timeslice(M, breaks=None, k=5):
    """
    Splits a bibliographic DataFrame into time intervals.

    Args:
        M (pd.DataFrame): Bibliographic DataFrame with a 'PY' (Publication Year) column.
        breaks (list or None): Numeric vector of two or more break points. If not provided, it is calculated automatically.
        k (int): Number of intervals to split the DataFrame into (used only if `breaks` is not provided). Default is 5.

    Returns:
        dict: Dictionary containing DataFrames for each sub-period.
    """
    M = M.get()

    # Convert the 'PY' column to numeric
    M['PY'] = pd.to_numeric(M['PY'], errors='coerce')
    py_clean = M['PY'].dropna()
    if py_clean.empty:
        raise ValueError("No valid publication years (PY) found in the dataset.")
        
    min_py = int(py_clean.min())
    max_py = int(py_clean.max())
    
    # Calculate breakpoints if not provided
    if breaks is None or (isinstance(breaks, list) and len(breaks) == 0):
        auto_breaks = np.floor(np.linspace(min_py, max_py + 1, k + 1))
        breaks = sorted(list(set(int(b) for b in auto_breaks)))
    else:
        # Keep only user breaks that are strictly between min_py and max_py + 1
        cleaned_breaks = sorted(list(set(int(b) for b in breaks)))
        middle_breaks = [b for b in cleaned_breaks if min_py < b < max_py + 1]
        breaks = [min_py] + middle_breaks + [max_py + 1]
        # Ensure unique and monotonic
        breaks = sorted(list(set(breaks)))

    # print("breaks:", breaks)
    
    # Split the data into intervals
    M['interval'] = pd.cut(M['PY'], bins=breaks, right=False)
    
    # Get the interval levels
    intervals = M['interval'].cat.categories
    indices = M['interval'].cat.codes
    
    # Split the DataFrame based on intervals
    split_df = {str(interval): M[M['interval'] == interval].drop(columns=['interval']) for interval in intervals}
    
    return split_df


def normalize_to_minus1_1(values):
    values = np.array(values)
    return 2 * (values - values.min()) / (values.max() - values.min()) - 1


def plot_thematic_evolution(
    Nodes,
    Edges,
    min_flow=0,
    measure="weighted",  # "inclusion", "stability", "weighted"
    label_size=5,
    edge_scale=10,
    node_scale=30
):
    # Choose the metric for edge weight
    if measure == "inc_index":
        edge_weight_var = "Inclusion"
    elif measure == "inc_weight_word_occ":
        edge_weight_var = "Inc_Weighted"
    elif measure == "stab_index":
        edge_weight_var = "Stability"
    else:
        edge_weight_var = "Inc_Weighted"

    # Amplify stability for visualization
    Edges = Edges.copy()
    Edges["Stability"] = Edges["Stability"] * 10

    # X coordinates for time slices
    unique_slices = sorted(Nodes["slice"].unique())
    
    # X coordinates
    Nodes = Nodes.copy()
    # Map slices to an evenly spaced grid between 0.2 and 0.7
    unique_slices = sorted(Nodes["slice"].unique())
    x_positions = np.linspace(0.1, 0.9, len(unique_slices))
    x_positions_dict = {s: x for s, x in zip(unique_slices, x_positions)}
    Nodes["x"] = Nodes["slice"].map(x_positions_dict)

    # Y coordinates to avoid overlap
    Nodes["y"] = Nodes.groupby("slice").cumcount()
    Nodes["y"] = Nodes.groupby("slice")["y"].transform(lambda y: normalize_to_minus1_1(y))
    # Scale y for better vertical separation
    Nodes["y"] = Nodes["y"] * 400

    # Prepare nodes for visualization
    Nodes_vis = Nodes.copy()
    Nodes_vis["shape"] = "box"
    Nodes_vis["size"] = Nodes_vis["sum"] * node_scale
    Nodes_vis["value"] = Nodes_vis["sum"]
    Nodes_vis["fixed_x"] = True
    Nodes_vis["fixed_y"] = True
    Nodes_vis["title"] = Nodes_vis["label"]

    num_nodes = len(Nodes_vis)
    cmap = plt.get_cmap("tab20" if num_nodes <= 20 else "hsv")
    # Use a pastel colormap for lighter, more pleasant colors
    pastel_cmap = plt.get_cmap("Pastel1" if num_nodes <= 9 else "tab20c")
    colors = [pastel_cmap(i % pastel_cmap.N) for i in range(num_nodes)]
    # Convert RGBA colors to hex strings
    Nodes_vis["color"] = [to_hex(c) for c in colors]

    # Ensure id exists and is unique
    if "id" not in Nodes_vis.columns:
        Nodes_vis = Nodes_vis.reset_index(drop=True)
        Nodes_vis["id"] = Nodes_vis.index

    # Normalize x coordinates to a suitable vis.js scale (e.g., 0-1000)
    Nodes_vis["x"] = Nodes_vis["x"] * 1000
    # Center y at 0 and scale to 0-800
    Nodes_vis["y"] = (Nodes_vis["y"] - Nodes_vis["y"].mean()) + 400

    # Prepare final nodes
    Nodes_vis = Nodes_vis[
        ["id", "label", "title", "group", "color", "x", "y", "shape", "size", "value", "fixed_x", "fixed_y"]
    ]
    Nodes_vis = pd.concat([Nodes_vis], ignore_index=True)

    # Prepare edges
    Edges_vis = Edges.copy()
    Edges_vis["width"] = Edges_vis[edge_weight_var] * edge_scale
    Edges_vis["value"] = Edges_vis[edge_weight_var]
    Edges_vis = Edges_vis[Edges_vis["value"] >= min_flow].copy()
    Edges_vis["color"] = [{"color": "#D3D3D3", "highlight": "#35343370", "hover": "#35343370"}] * len(Edges_vis)

    # Remove self-loop edges
    Edges_vis = Edges_vis[Edges_vis["from"] != Edges_vis["to"]].copy()

    # Build the network
    net = Network(height="98vh", width="100%", notebook=True, cdn_resources="in_line", directed=True)
    for _, node in Nodes_vis.iterrows():
        # Ensure title is always a string and not NaN/float
        node_title = node["title"] if "title" in node and pd.notnull(node["title"]) else node["label"]
        if not isinstance(node_title, str):
            node_title = str(node_title)
        net.add_node(
            node["id"],
            label=node["label"] if isinstance(node["label"], str) else str(node["label"]),
            title=node_title,
            x=node["x"],
            y=node["y"],
            size=node["size"],
            color=node.get("color", "blue"),
            shape=node.get("shape", "box"),
            fixed={"x": node["fixed_x"], "y": node["fixed_y"]},
        )

    # Ensure arrows go from 'from' to 'to' (correct direction)
    for _, edge in Edges_vis.iterrows():
        net.add_edge(
            int(edge["from"]),
            int(edge["to"]),
            value=edge["value"],
            width=edge["width"],
            color=edge["color"],
            title=f"Weight: {edge['value']}",
            arrows="to"
        )

    # Configure physics and interactions
    net.toggle_physics(False)
    net.set_options("""
        var options = {
            "nodes": {
                "shape": "box",
                "widthConstraint": {"minimum": 200, "maximum": 200}
            },
            "edges": {
                "smooth": {"type": "horizontal"},
                "arrows": {"to": {"enabled": true}},
                "scaling": {"min": 1, "max": %d}
            },
            "physics": {"enabled": false},
            "interaction": {
                "dragNodes": true,
                "hideEdgesOnDrag": true,
                "navigationButtons": false,
                "zoomSpeed": 0.4
            },
            "manipulation": {"enabled": false}
        }
    """ % edge_scale)

    return net


def rgba_to_hex(rgba):
    return '#%02x%02x%02x' % tuple(int(255 * c) for c in rgba[:3])
