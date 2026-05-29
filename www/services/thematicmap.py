from .utils import *
from .igraph2vis import *
from .termextraction import *
from .biblionetwork import *


def thematic_map(df, field="ID", n=250, minfreq=5, ngrams=1, stemming=False, size=0.5, n_labels=1, community_repulsion=0.1, repel=True, remove_terms=None, synonyms=None, cluster="walktrap", subgraphs=False):
        # df = metaTagExtraction(df, field=field)
        M = df
        m = df.get()

        # Set ngrams based on field
        ngrams = int(ngrams) if field in ['TI', 'AB'] else 1
        # Set stemming as boolean
        stemming = True if stemming == "Yes" else False
        minfreq = max(0, int(minfreq * len(m) // 1000))

        # Preprocess field and create network matrix
        if field == "ID":
            NetMatrix = biblionetwork(M, analysis="co-occurrences", network="keywords", n=n, sep=";", remove_terms=remove_terms, synonyms=synonyms)
        elif field == "DE":
            NetMatrix = biblionetwork(M, analysis="co-occurrences", network="author_keywords", n=n, sep=";", remove_terms=remove_terms, synonyms=synonyms)
        elif field == "TI":
            M = term_extraction(M, field="TI", ngrams=ngrams, verbose=False, stemming=stemming, remove_terms=remove_terms, synonyms=synonyms)
            NetMatrix = biblionetwork(M, analysis="co-occurrences", network="titles", n=n, sep=";")
        elif field == "AB":
            M = term_extraction(M, field="AB", ngrams=ngrams, verbose=False, stemming=stemming, remove_terms=remove_terms, synonyms=synonyms)
            NetMatrix = biblionetwork(M, analysis="co-occurrences", network="abstracts", n=n, sep=";")
        else:
            raise ValueError("Invalid field specified.")

        if NetMatrix is not None and not NetMatrix.empty:
            Net = network_plot(NetMatrix, normalize="association", Title="Keyword co-occurrences", type="auto",
                       labelsize=n_labels, halo=False, cluster=cluster, remove_isolates=True,
                       community_repulsion=community_repulsion, remove_multiple=False, noloops=True,
                       weighted=True, label_cex=True, edgesize=5, size=1, edges_min=1, verbose=False)
        else:
            print("\n\nNetwork matrix is empty!\nThe analysis cannot be performed\n\n")
            return None
        
        S = Net['S']

        # Set row and column names to lowercase
        NetMatrix.index = NetMatrix.columns = NetMatrix.index.str.lower()

        # Get graph and clusters
        net = Net['graph']
        net_groups = Net['cluster_obj']
        group = net_groups.membership
        # Extract words and their groups from net_groups
        word = net.vs['name']
        color = net.vs['color']
        color = ["#D3D3D3" if c is None else c for c in color]

        # Find common words between NetMatrix and word list
        W = list(NetMatrix.index.intersection(word))
        # Get indices from NetMatrix
        index = NetMatrix.index.isin(W)
        # Get indices from word list
        ii = [i for i, w in enumerate(word) if w in W]
        # Update word, group and color lists to keep only matched elements
        word = [word[i] for i in ii]
        group = [group[i] for i in ii]
        color = [color[i] for i in ii]
        # Calculate diagonal matrix C and subset matrices
        C = np.diag(NetMatrix.values)
        S = NetMatrix.values  # Get the similarity matrix
        sEij = pd.DataFrame(S[np.ix_(index, index)], index=NetMatrix.index[index], columns=NetMatrix.columns[index])
        sC = C[index]

        # Create dataframe with word data
        df_lab = pd.DataFrame({
            'sC': sC,
            'words': word,
            'groups': group,
            'color': color,
            'cluster_label': 'NA'
        })
        
        # Filter and process cluster data
        df_lab_filtered = df_lab[df_lab['sC'] >= minfreq]
        if df_lab_filtered.empty:
            print("\n\nNo keywords met the minimum frequency threshold!\n\n")
            return None

        df_lab = (df_lab_filtered
                .groupby('groups')
                .apply(lambda x: pd.Series({
                    'freq': x['sC'].sum(),
                    'cluster_label': x.loc[x['sC'].idxmax(), 'words'],
                    'sC': list(x['sC']),
                    'words': list(x['words']),
                    'color': x['color'].iloc[0]
                }))
                .reset_index())

        # Explode both words and sC columns to create rows for each word and its occurrence count
        df_lab = df_lab.assign(
            words=df_lab['words'],
            sC=df_lab['sC']
        ).explode(['words', 'sC']).reset_index(drop=True)

        # Convert to upper triangle matrix and create edge dataframe
        index_names = sEij.index
        column_names = sEij.columns
        sEij = triu(sEij.values)
        
        df_lab_top = df_lab[['words', 'groups']].reset_index(drop=True)

        # Create edge list dataframe
        sEij_df = pd.DataFrame(sEij, index=index_names, columns=column_names)
        # sEij_df['words1'] = sEij_df.index

        sEij_df = pd.DataFrame(sEij_df.values, index=sEij_df.index, columns=sEij_df.columns)
        sEij_df = sEij_df.reset_index(names=['words1'])
        sEij_df = pd.melt(sEij_df, id_vars=['words1'], var_name='words2', value_name='eij')
        sEij_df = sEij_df[sEij_df['eij'] > 0]

        sEij_df['words1'] = sEij_df['words1'].astype(str)
        df_lab_top['words'] = df_lab_top['words'].astype(str)
        df_lab['words'] = df_lab['words'].astype(str)

        # Perform left joins equivalent to R's left_join operations
        sEij_df = sEij_df.merge(df_lab_top[['words', 'groups']], 
                       left_on='words1', 
                       right_on='words', 
                       how='left')
        sEij_df = sEij_df.merge(df_lab_top[['words', 'groups']], 
                       left_on='words2', 
                       right_on='words', 
                       how='left',
                       suffixes=('', '2'))
        
        # Drop the extra 'words' columns created by the merge
        sEij_df = sEij_df.drop(['words', 'words_y'], axis=1, errors='ignore')

        # Get top row for each group
        df_lab_top = (df_lab[['groups', 'cluster_label', 'color', 'freq']]
                  .groupby('groups')
                  .first()
                  .reset_index())

        # Remove duplicate columns
        sEij_df = sEij_df.loc[:, ~sEij_df.columns.duplicated()]
        
        # Clean the words column by splitting on newlines and taking first value
        df_lab['words'] = df_lab['words'].str.split('\n').str[0]
        # Clean up words by removing leading numbers and whitespace
        df_lab['words'] = df_lab['words'].str.replace(r'^\s*\d+\s*', '', regex=True).str.strip()

        df = sEij_df[
                sEij_df['words1'].isin(df_lab['words'].unique()) & 
                sEij_df['words2'].isin(df_lab['words'].unique())
        ]

        # Controlliamo se la colonna 'eij' esiste prima di continuare
        if 'eij' not in sEij_df.columns:
            raise KeyError("La colonna 'eij' non esiste in sEij_df!")

        # Controlliamo il filtraggio per evitare DataFrame vuoti
        filtered_df = sEij_df[
            sEij_df['words1'].isin(df_lab['words'].unique()) & 
            sEij_df['words2'].isin(df_lab['words'].unique())
        ]

        if filtered_df.empty:
            raise ValueError("Il filtro ha eliminato tutte le righe! Controlla i dati in df_lab['words'] e sEij_df['words1', 'words2'].")

        # 3. Filtra correttamente i dati
        df = (
            filtered_df
            .assign(ext=lambda x: (x['groups'] != x['groups2']).astype(int))
            .groupby('groups')
            .agg({
            'words1': lambda x: len(set(x)),
            'eij': lambda x: sum(x * x.index),      # calculate centrality as sum(eij*ext)
            'ext': lambda x: sum(x.index * (1-x))   # calculate density as sum(eij*(1-ext))
            })
            .rename(columns={
            'words1': 'n',
            'eij': 'CallonCentrality',
            'ext': 'CallonDensity'
            })
            .assign(
            CallonDensity=lambda x: x['CallonDensity'] / x['n'] * 100,
            RankCentrality=lambda x: x['CallonCentrality'].rank(),
            RankDensity=lambda x: x['CallonDensity'].rank()
            )
            .merge(df_lab_top, on='groups', how='left')
            .rename(columns={'cluster_label': 'Cluster', 'freq': 'ClusterFrequency'})
            .reset_index()
        )

        # Calculate plot parameters
        meandens = df['RankDensity'].mean()
        meancentr = df['RankCentrality'].mean()
        rangex = max(meancentr - df['RankCentrality'].min(), df['RankCentrality'].max() - meancentr)
        rangey = max(meandens - df['RankDensity'].min(), df['RankDensity'].max() - meandens)

        # Create annotations dataframe for quadrant labels
        xlimits = [meancentr - (rangex * 1.2), meancentr + (rangex * 1.2)]
        ylimits = [meandens - (rangey * 1.2), meandens + (rangey * 1.2)]
        
        # Create annotations dataframe
        annotations = pd.DataFrame({
            'xpos': sorted(xlimits + xlimits),
            'ypos': ylimits + ylimits,
            'words': ['Emerging or\nDeclining Themes', 'Niche Themes', 'Basic Themes', 'Motor Themes'],
            'hjustvar': [0, 0, 1, 1],
            'vjustvar': [0, 1, 0, 1]
        })

        # Calculate size parameters
        min_size = 5 * (1 + size)  # Changed from 10 to 5 to match R version
        max_size = 30 * (1 + size)

        # Create base plot using plotly express
        fig = px.scatter(
            df,
            x='RankCentrality',
            y='RankDensity',
            color=df.index.map(lambda x: f"rgba{tuple(int(c * 255) for c in color[x][:3]) + (0.5,)}" if isinstance(color[x], tuple) else color[x]),  # Handle tuple colors
            labels={'RankCentrality': 'Relevance degree\n(Centrality)', 'RankDensity': 'Development degree\n(Density)'},  # Updated labels
            opacity=0,
        )

        fig.update_traces(hoverinfo='skip', hovertemplate=None)

        # Add quadrant lines with transparency
        fig.add_hline(y=meandens, line_dash="dash", line_color="rgba(0,0,0,0.7)")
        fig.add_vline(x=meancentr, line_dash="dash", line_color="rgba(0,0,0,0.7)")

        # Add annotations for quadrants
        for _, row in annotations.iterrows():
            fig.add_annotation(
            x=row['xpos'],
            y=row['ypos'],
            text=row['words'],
            showarrow=False,
            xanchor='left' if row['hjustvar'] == 0 else 'right',
            yanchor='bottom' if row['vjustvar'] == 0 else 'top',
            font=dict(size=12*(1+size), color='rgba(32,32,32,0.5)')
            )

        # Add labels if size > 0
        if size > 0:
            text_size = 10 * (1 + size)
            
            if repel:
                for cluster_id, cluster_data in df.groupby('groups'):
                    cluster_center_x = cluster_data['RankCentrality'].mean()
                    cluster_center_y = cluster_data['RankDensity'].mean()
                    cluster_size = cluster_data['ClusterFrequency'].sum()

                    # Get the top three most frequent words for the cluster
                    top_words = (df_lab[df_lab['groups'] == cluster_id]
                        .sort_values('sC', ascending=False)
                        .head(3)['words']
                        .str.lower()
                        .tolist())
                    top_words_text = '\n'.join(top_words)

                    # Get all words with occurrences for hover text
                    hover_words = []
                    df_sorted = df_lab[df_lab['groups'] == cluster_id].sort_values('sC', ascending=False)
                    for idx, row in enumerate(df_sorted.head(10).itertuples()):
                        hover_words.append(f"{row.words}: {row.sC}")
                    hover_text = '<br>'.join(hover_words)

                    size_bubble = min_size + (max_size - min_size) * np.log1p(cluster_size) / np.log1p(df['n'].max()) * 3

                    # Add labels for the cluster with top three words
                    fig.add_trace(go.Scatter(
                    x=[cluster_center_x],
                    y=[cluster_center_y],
                    text=[top_words_text.replace('\n', '<br>')],
                    hovertext=[hover_text],
                    hoverinfo='text',
                    mode='markers+text',
                    textposition='middle center',
                    textfont=dict(size=text_size),
                    marker=dict(
                        size=size_bubble,
                        sizemin=100,
                        sizemode='diameter',
                        color=cluster_size,
                        colorscale='Viridis',
                        line=dict(width=1, color='DarkSlateGrey'),
                        opacity=0.5,
                    ),
                    showlegend=False
                    ))

        # Update layout
        fig.update_layout(
            height=800,
            showlegend=False,
            plot_bgcolor='white',
            xaxis=dict(
            title="Relevance degree\n(Centrality)",
            showgrid=False,
            showticklabels=False,
            showline=True,
            linewidth=0.5,
            linecolor='black',
            zeroline=False,
            range=xlimits
            ),
            yaxis=dict(
            title="Development degree\n(Density)",
            showgrid=False,
            showticklabels=False,
            showline=True,
            linewidth=0.5,
            linecolor='black',
            zeroline=False,
            range=ylimits
            )
        )
        fig = go.FigureWidget(fig)
        fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                     'displaylogo': False}

        ##############################################################################################################################################

        # Rename and rearrange columns in df_lab
        df_lab.columns = ['Cluster', 'Cluster_Frequency', 'Cluster_Label', 'Occurrences', 'Words', 'Color']
        df_lab = (df_lab
             .sort_values('Cluster')
             .dropna(subset=['Color'])
             .assign(Cluster=lambda x: pd.factorize(x['Cluster'])[0] + 1))

        # Add centrality measure to words
        cluster_res = Net['cluster_res']
        df_lab = df_lab.merge(cluster_res, left_on='Words', right_on='vertex', how='left')
        
        # Keep only the specified columns
        df_lab = df_lab[['Occurrences', 'Words', 'Cluster', 'Cluster_Label', 'btw_centrality', 'clos_centrality', 'pagerank_centrality']]
        df = df[['Cluster', 'CallonCentrality', 'CallonDensity', 'RankCentrality', 'RankDensity', 'ClusterFrequency']]

        # Handle document clustering
        document_to_clusters = cluster_assignment(M=m, words=df_lab, field=field, remove_terms=remove_terms, synonyms=synonyms, threshold=0.5)

        # Create parameters dictionary and unpack into dataframe
        params = {
            'field': field,
            'n': n,
            'minfreq': minfreq,
            'ngrams': ngrams,
            'stemming': stemming, 
            'size': size,
            'n_labels': n_labels,
            'community_repulsion': community_repulsion,
            'repel': repel,
            'remove_terms': remove_terms,
            'synonyms': synonyms,
            'cluster': cluster
        }

        # Unpack nested params into flat key-value pairs
        flat_params = []
        for k,v in params.items():
            if isinstance(v, (list, dict)):
                for i,val in enumerate(v):
                    flat_params.append((f"{k}{i+1}", val))
            else:
                flat_params.append((k,v))
                
        params_df = pd.DataFrame(flat_params, columns=['params', 'values'])

        # Handle subgraphs
        if subgraphs:
            gcl = {}
            colors = df['color'].unique()
            for color in colors:
                node_indices = [i for i,v in enumerate(Net['graph'].vs) 
                               if v['color'] == color]
                gcl[color] = Net['graph'].subgraph(node_indices)
        else:
            gcl = None

        ################################## NETWORK VISUALIZATION ##################################
        node_opacity = 0.5
        net = Network(height="98vh", width="100%", notebook=True, cdn_resources="in_line")
        net.toggle_physics(False)

        # Use colors from df['adjusted_color']
        unique_clusters = set(Net['cluster_obj'].membership)
        cluster_colors = {}
        cm_clusters = cluster_res

        # Get unique cluster IDs and their colors
        for cluster_id in unique_clusters:
            # Generate random RGB values
            r = np.random.randint(0, 255)
            g = np.random.randint(0, 255) 
            b = np.random.randint(0, 255)
            # Create rgba color with 0.3 opacity
            cluster_colors[cluster_id] = f"rgba({r},{g},{b},{node_opacity})"  #da aggiustare l'opacity

        # Generate layout
        # Using default igraph layout
        layout = Net['graph']['layout']
        # Get coordinates from layout
        coords = np.array([[pos[0], pos[1]] for pos in layout])
        
        # Scale coordinates to fit 800px height
        # First normalize to [-1,1] range
        coords = coords / np.abs(coords).max()
        
        # Then scale to target dimensions
        # Width will be proportional to maintain aspect ratio
        coords[:, 0] *= 1000  # Scale x coordinates 
        coords[:, 1] *= 400   # Scale y coordinates to fit 800px (centered)

        # Prepare for avoid_net_overlaps
        node_labels = [v["name"] if "name" in v.attributes() else f"Node {v.index}" for v in Net['graph'].vs]
        node_sizes = []
        nodes = []
        
        # Add nodes with matching R visNetwork settings
        for idx, vertex in enumerate(Net['graph'].vs):
            cluster_id = Net['cluster_obj'].membership[vertex.index]
            node_color = cluster_colors[cluster_id]

            # Normalize node sizes
            min_deg, max_deg = min(Net['graph'].degree()), max(Net['graph'].degree())
            node_size = 10 if max_deg == min_deg else (15 * (vertex.degree() - min_deg) / (max_deg - min_deg) + 10)
            node_size = max(10, min(130, node_size))
            font_size = node_size * 2
            node_sizes.append(node_size)
            
            # Calculate font opacity using R-like formula
            min_font_size = 10   # Minimum node size 
            max_font_size = 130  # Maximum node size 
            font_opacity = np.sqrt((font_size - min_font_size) / (max_font_size - min_font_size))*node_opacity + 0.3
            font_opacity = max(0.1, min(1, font_opacity))  # Clamp between 0.1 and 1
            
            nodes.append({
                'id': vertex.index,
                'label': vertex["name"] if "name" in vertex.attributes() else f"Node {vertex.index}",
                'title': vertex["name"] if "name" in vertex.attributes() else f"Node {vertex.index}",
                'color': node_color,
                'size': node_size,
                'font': {
                    'size': font_size, 
                    'color': f'rgba(0,0,0,{font_opacity})', 
                },
                'x': layout[idx][0] * 1000,
                'y': layout[idx][1] * 1000
            })

        # Remove overlapping labels
        noOverlap = True
        if noOverlap:
            threshold = 0.05
            ymax = np.ptp(coords[:, 1])  # equivalent to diff(range())
            xmax = np.ptp(coords[:, 0])
            threshold2 = threshold * np.mean([xmax, ymax])
            
            # Create data structure for overlap checking
            labels_to_remove = avoid_net_overlaps(coords, node_labels, node_sizes, threshold=threshold2)
        else:
            labels_to_remove = []
        #labels_to_remove = avoid_net_overlaps(coords, node_labels, node_sizes, threshold=0.05)
        
        # Add nodes to network
        unique_nodes = {node['id']: node for node in nodes}.values()
        for node in unique_nodes:
            if node['label'] in labels_to_remove:
                node['label'] = ''
            net.add_node(node['id'], **node)

        # Add edges with improved styling matching R implementation
        added_edges = set()
        edge_weights = [e.attributes().get('weight', 1) for e in Net['graph'].es]
        max_weight = max(edge_weights) if edge_weights else 1
        
        for edge in Net['graph'].es:
            source, target = edge.tuple
            cluster_source = Net['cluster_obj'].membership[source]
            cluster_target = Net['cluster_obj'].membership[target]
            
            # Set edge color with proper opacity
            if cluster_source == cluster_target:
                base_color = cluster_colors[cluster_source]
                # Convert rgba to hex with opacity
                rgba_values = [int(x) for x in base_color[5:-1].split(',')[:-1]]
                edge_color = f"rgba({rgba_values[0]},{rgba_values[1]},{rgba_values[2]},0.56)"
            else:
                # Use darker gray for inter-cluster edges (equivalent to #69696960 in R)
                edge_color = "rgba(105,105,105,0.38)"
            
            # Calculate edge width similar to R implementation
            edge_weight = edge.attributes().get('weight', 1)
            normalized_weight = (edge_weight ** 2 / (max_weight ** 2)) * (10 + 2.5)  # 2.5 is base edge size
            
            edge_tuple = (source, target) if source < target else (target, source)
            
            # Add edge if not already added
            if edge_tuple not in added_edges:
                net.add_edge(
                    source, 
                    target, 
                    color=edge_color,
                    width=normalized_weight,
                    smooth={'type': 'horizontal'},
                    dashes=False  # Set to True if you have line type information
                )
                added_edges.add(edge_tuple)

        # Configure network options to match R visNetwork
        node_shadow = False
        edit_nodes = False
        net.set_options(f"""
            var options = {{
                "nodes": {{
                    "shadow": {"true" if node_shadow else "false"}
                }},
                "edges": {{
                    "smooth": {{"type": "horizontal"}}
                }},
                "interaction": {{
                    "dragNodes": true,
                    "hideEdgesOnDrag": true,
                    "navigationButtons": false,
                    "zoomSpeed": 0.4
                }},
                "physics": {{
                    "enabled": false
                }},
                "manipulation": {{
                    "enabled": {"true" if edit_nodes else "false"}
                }}
            }}
        """)

        # Save network to HTML
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        html_path = tmp.name
        with open(html_path, 'w', encoding="utf-8") as f:
            html = net.generate_html()
            new_css = "     .card {\n                 border: none;\n             }"
            updated_html = html.replace("</style>", new_css + "\n        </style>")
            updated_html = updated_html.replace("1px solid lightgray", "none")
            
            f.write(updated_html)

        ################################################################################################

        # Return results dictionary 
        results = {
            'map': fig,
            'clusters': df,
            'words': df_lab,
            'nclust': len(df),
            'net': Net,
            'subgraphs': gcl,
            'documentToClusters': document_to_clusters,
            'params': params_df
        }

        return results['map'], html_path.split(os.sep)[-1], results['words'], results['clusters'], results['documentToClusters']


def cluster_assignment(M, words, field, remove_terms=None, synonyms=None, threshold=0.5):
    # Integrate stopwords and synonyms in M original field
    if field in ["AB", "TI"]:
        field = f"{field}_TM"

    # Check if field exists in M
    Fi = M[field]
    
    # Create lists to store terms and SR values
    all_terms = []
    all_sr = []
    
    # Iterate through each row
    for i, terms_list in enumerate(Fi):
        if isinstance(terms_list, list):
            for term in terms_list:
                if term:  # Skip empty terms
                    all_terms.append(term.strip())
                    all_sr.append(M['SR'].iloc[i])
    
    all_field = pd.DataFrame({
        'terms': all_terms,
        'SR': all_sr
    })

    # Remove terms if specified
    if remove_terms is not None:
        remove_terms = pd.DataFrame({'terms': [t.strip().upper() for t in remove_terms]})
        all_field = all_field.merge(remove_terms, on='terms', how='left', indicator=True)
        all_field = all_field[all_field['_merge'] == 'left_only'].drop('_merge', axis=1)

    # Handle synonyms
    if synonyms is not None:
        s = [syn.upper().split(";") for syn in synonyms]
        snew = [l[0] for l in s]
        sold = [l[1:] for l in s]
        syn = pd.DataFrame({
            'new': np.repeat(snew, [len(x) for x in sold]),
            'terms': [item.strip() for sublist in sold for item in sublist]
        })
        all_field = all_field.merge(syn, on='terms', how='left')
        all_field.loc[all_field['new'].notna(), 'terms'] = all_field.loc[all_field['new'].notna(), 'new']
        all_field = all_field[['SR', 'terms']]

    # Process words dataframe
    words = words.assign(
        p_w=1/words['Occurrences'],
        p_c=words['pagerank_centrality']
    )
    
    # Save a copy of the ungrouped dataframe for merging
    words_for_merge = words.copy()
    
    # Continue with groupby operation for later use if needed
    words = words.groupby('Cluster')

    # Merge terms with words
    # Convert 'terms' to string before applying string operations
    all_field['terms'] = all_field['terms'].astype(str)
    terms = all_field.assign(terms=all_field['terms'].str.lower()).merge(
        words_for_merge, left_on='terms', right_on='Words', how='left'
    )

    # Calculate probabilities
    terms = (terms.groupby('SR')
        .apply(lambda x: x.assign(pagerank=x['p_c'].sum()))
        .reset_index(drop=True)
        .groupby(['SR', 'Cluster_Label'])
        .agg({'p_w': 'sum', 'p_c': 'max'})
        .reset_index()
        .rename(columns={'p_c': 'pagerank'}))

    terms['p'] = terms['p_w'] / terms.groupby('SR')['p_w'].transform('sum')
    terms = terms.dropna(subset=['Cluster_Label']).drop('p_w', axis=1)

    # Assign clusters based on threshold
    terms_max = (terms[terms['p'] >= threshold]
        .sort_values('p', ascending=False)
        .groupby('SR')
        .agg({'Cluster_Label': lambda x: ';'.join(x)})
        .rename(columns={'Cluster_Label': 'Assigned_cluster'}))

    # Calculate pagerank for assigned clusters
    terms_pagerank = (terms.merge(terms_max, on='SR')
        .query('Cluster_Label == Assigned_cluster')[['SR', 'pagerank']])

    # Pivot and merge results
    terms = (terms.drop('pagerank', axis=1)
        .pivot(index='SR', columns='Cluster_Label', values='p')
        .reset_index()  # Ensure SR is only a column
        .rename_axis(None, axis=1)  # Remove any index name
    )
    # Now merge with terms_max and terms_pagerank
    terms = terms.merge(terms_max, on='SR').merge(terms_pagerank, on='SR')

    # Process final results
    if 'DI' not in M.columns:
        M['DI'] = np.nan
    year = pd.Timestamp.now().year + 1
    
    M = M.reset_index(drop=True)
    terms = (M.assign(
        TCpY=lambda x: x['TC']/(year-x['PY']),
        NTC=lambda x: x.groupby('PY')['TC'].transform(lambda y: y/y.mean())
    )[['DI', 'AU', 'TI', 'SO', 'PY', 'TC', 'TCpY', 'NTC', 'SR']]
        .merge(terms, on='SR')
        .fillna(0)
        .groupby('Assigned_cluster')
        .apply(lambda x: x.sort_values('TC', ascending=False))
        .reset_index(drop=True))

    return terms
