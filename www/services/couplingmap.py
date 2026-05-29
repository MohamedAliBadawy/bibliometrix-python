from .utils import *
from .cocmatrix import *
from .biblionetwork import *
from .termextraction import *
from .networkplot import *
from .histnetwork import *
from .metatagextraction import *
from .tabletag import *

def couplingMap(df, analysis="documents", field="CR", n=500, minfreq=5,
                ngrams=1, community_repulsion=0.1, impact_measure="local",
                stemming=False, size=0.5, label_term=None, n_labels=1, repel=True, clustering="walktrap"):
    
    if analysis not in ["documents", "authors", "sources"]:
        print('\nanalysis argument is incorrect.\n\nPlease select one of the following choices: "documents", "authors", "sources"\n\n')
        return None

    df = metaTagExtraction(df, "SR") # serve questo per avere il merging perfetto per uniformare la colonna SR
    M = df.get()

    ngrams = int(ngrams)
    minfreq = max(0, int(minfreq * len(M) // 1000))

    Net = network(df, analysis=analysis, field=field, stemming=stemming, n=n, community_repulsion=community_repulsion, cluster=clustering)
    if Net is None or 'graph' not in Net or Net['graph'] is None:
        raise ValueError(f"No coupling relationships can be calculated. The coupling field '{field}' is empty or has no common links in this dataset.")
    net = Net['graph']
  
    NCS = normalizeCitationScore(df, field=analysis, impact_measure=impact_measure)

    if impact_measure == "global":
        NCS['MNLCS'] = NCS['MNGCS']
        NCS['LC'] = NCS['TC']

    # Converte la prima colonna di NCS in maiuscolo
    NCS.iloc[:, 0] = NCS.iloc[:, 0].str.upper()

    # Deduplicate NCS on the key column to prevent the merge from producing more rows
    # than graph vertices (can happen when two papers share the same SR, e.g. same
    # first-author initials, year and source in Lens exports)
    NCS[analysis] = NCS[analysis].astype(str).str.upper()
    NCS = NCS.drop_duplicates(subset=[analysis], keep='first')

    # Label dei nodi del grafo
    label = pd.Series(net.vs['name'])

    # Get vertex names and create initial dataframes
    # First merge with NCS
    L = pd.DataFrame({'id': label.str.upper()})
    L.columns = [analysis]
    L[analysis] = L[analysis].astype(str).str.upper()
    D = L.merge(NCS, on=analysis, how='left', copy=True)
    D = D.fillna(0).reset_index(drop=True)

    # Second merge with cluster results
    Net['cluster_res'] = Net['cluster_res'].rename(columns={'vertex': analysis})
    Net['cluster_res'][analysis] = Net['cluster_res'][analysis].astype(str).str.lower()
    Net['cluster_res'] = Net['cluster_res'].drop_duplicates(subset=[analysis], keep='first')

    L2 = pd.DataFrame({'id': label.str.lower()})
    L2.columns = [analysis]
    C = L2.merge(Net['cluster_res'], on=analysis, how='left', copy=True)
    C = C.fillna(0).reset_index(drop=True)

    # Get group membership and colors
    group = Net['cluster_obj'].membership
    color = net.vs['color']

    # Convert colors to hex and handle NaN values
    color = [to_hex(c) if pd.notna(c) else "#D3D3D3" for c in color]

    # Safety check: if merge produced wrong number of rows, truncate/pad to match
    if len(D) != len(group):
        # Re-build D strictly from the graph labels (one row per node, no duplicates)
        D = pd.DataFrame({analysis: label.str.upper()}).merge(NCS, on=analysis, how='left').fillna(0)
        D = D.groupby(analysis, sort=False).first().reset_index()
        # Re-align to graph node order
        node_order = pd.DataFrame({analysis: label.str.upper(), '_order': range(len(label))})
        D = node_order.merge(D, on=analysis, how='left').sort_values('_order').drop(columns='_order').fillna(0).reset_index(drop=True)
        C = pd.DataFrame({analysis: label.str.lower()}).merge(Net['cluster_res'], on=analysis, how='left').fillna(0).reset_index(drop=True)

    D['group'] = group
    D['color'] = color


    DC = pd.concat([D, C.iloc[:, 1:]], axis=1)
    DC = DC.fillna(0)
    DC['name'] = DC.iloc[:, 0]
    
    # Resetta l'indice per evitare ambiguità
    DC = DC.reset_index(drop=True)
    
    # Raggruppa senza ambiguità
    df_lab = DC.groupby('group', as_index=False).apply(lambda x: x.assign(
        MNLCS2=x['MNLCS'].where(x['MNLCS'] >= 1),
        MNLCS=round(x['MNLCS'], 2),
        name=x['name'].str.lower(),
        freq=len(x)
    )).sort_values(by=['MNLCS'], ascending=False)

    df = df_lab.groupby('group').apply(lambda x: pd.Series({
        'freq': x['freq'].iloc[0],
        'centrality': x['pagerank_centrality'].mean() * 100,
        'impact': np.nan_to_num(x['MNLCS2'].mean(skipna=True)),
        'label_cluster': x['group'].iloc[0],
        'color': x['color'].iloc[0],
        'label': '\n'.join(x['name'].iloc[:min(n_labels, len(x))].tolist()),
        'words': '\n'.join((x['name'] + ' ' + x['MNLCS'].astype(str)).tolist())
    })).reset_index()

    df['centrality'] = df['centrality'].fillna(0.0)
    df['impact'] = df['impact'].fillna(0.0)
    df['rcentrality'] = df['centrality'].rank()
    df['rimpact'] = df['impact'].rank()

    meandens = df['rimpact'].mean()
    meancentr = df['rcentrality'].mean()
    if pd.isna(meandens): meandens = 0.0
    if pd.isna(meancentr): meancentr = 0.0
    df = df[df['freq'] >= minfreq]

    df_lab = df_lab[df_lab['group'].isin(df['group'])]
    df_lab = df_lab.iloc[:, [0, 6, 14, 7, 3]]
    df_lab.columns = [analysis, "Cluster", "ClusterFrequency", "ClusterColor", "NormalizedLocalCitationScore"]

    df_lab['ClusterName'] = df_lab['Cluster'].map(df.set_index('group')['label'])

    M = M.reset_index(drop=True)

    if label_term is None:
        label_term = "null"
    if label_term in ["DE", "ID", "TI", "AB"]:
        w = labeling(M, df_lab, term=label_term, n=n, n_labels=n_labels, analysis=analysis, ngrams=ngrams)
        df['label'] = w

    df['freq'] = df['freq'].fillna(1.0).replace(0, 1.0)
    df['log_freq'] = np.log(df['freq'])
    df['log_freq'] = df['log_freq'].fillna(0.0).replace([np.inf, -np.inf], 0.0)
    df['adjusted_color'] = df['color'].apply(lambda x: adjust_color(x, alpha=0.5))

    # Clean df completely before px.scatter is initialized
    df = df.fillna(0)
    df = df.replace([np.inf, -np.inf], 0)

    ################## FIGURE ##################
    # Calculate range for bubble sizes based on size parameter
    x_max = df['rcentrality'].max()
    x_range = np.ptp(df['rcentrality'])
    y_min = df['rimpact'].min()
    y_range = np.ptp(df['rimpact'])

    # Calcola x e y (aggiungiamo +0.5 a entrambi gli estremi come in R)
    x1 = x_max - 0.02 - (x_range * 0.125) + 0.5
    x2 = x_max - 0.02 + 0.5
    y1 = y_min
    y2 = y_min + (y_range * 0.125)

    # Format hover text for Plotly with proper line breaks
    # We need to replace newlines with HTML breaks for the hover text in Plotly
    
    # Function to limit to first 10 items
    def limit_to_first(text):
        if pd.isna(text):
            return ""
        lines = text.split('\n')
        if len(lines) > 10:
            lines = lines[:10]
            lines.append('...')  # Add ellipsis to show there are more items
        return '\n'.join(lines)
    
    # Apply the function to limit each entry to 20 items
    df['words'] = df['words'].apply(limit_to_first)
    
    # Replace newlines with HTML breaks for Plotly hover display
    df['words_daccapo'] = df['words'].str.replace('\n', '<br>')
    
    # Ensure words column is properly formatted for hover display
    for i, row in df.iterrows():
        if pd.isna(row['words_daccapo']):
            df.at[i, 'words_daccapo'] = ""

    # Crea il grafico di base
    fig = px.scatter(
        df,
        x='rcentrality',
        y='rimpact',
        size=df['log_freq'] * 15,  # Multiply log_freq by 15
        color_discrete_sequence=df['adjusted_color'],  # Use pre-adjusted colors
        hover_name='words_daccapo',
        labels={'rcentrality': 'Centrality', 'rimpact': 'Impact'},
    )
    
    fig.update_layout(
        autosize=True,
        width=None,
        height=None,
        margin=dict(l=0, r=0, t=0, b=0)
    )

    # Create custom hover template instead of using words_daccapo column
    fig.update_traces(
        hovertemplate='<b>%{hovertext}</b><extra></extra>',
        hovertext=[words.replace('\n', '<br>') for words in df['words']]
    )

    # Remove the words_daccapo column as it's no longer needed
    if 'words_daccapo' in df.columns:
        df = df.drop('words_daccapo', axis=1)

    # Aggiungi linee orizzontali e verticali
    fig.add_hline(y=meandens, line_dash="dash", line_color="rgba(0,0,0,0.7)")
    fig.add_vline(x=meancentr, line_dash="dash", line_color="rgba(0,0,0,0.7)")

    # Aggiorna le proprietà dei marker per replicare R
    min_size = 10 * (1 + size)
    max_size = 30 * (1 + size)
    
    # Calculate size reference for correct scaling
    max_log_freq = max(df['log_freq']) if not df.empty else 0.0
    if pd.isna(max_log_freq) or max_log_freq <= 0:
        max_log_freq = 1.0
    sizeref = 2.0 * max_log_freq / (max_size**2)
    if pd.isna(sizeref) or sizeref <= 0:
        sizeref = 1.0
    
    fig.update_traces(
        marker=dict(
            color=df['adjusted_color'],  # Use adjusted color with transparency
            symbol='circle',
            sizemode='area',
            sizemin=min_size,
            sizeref=sizeref,  # Dynamic sizing based on log_freq range
            line=dict(width=10)  # Border for points
        )
    )

    # Aggiunge le etichette se size > 0
    if size > 0 and not df.empty:
        # Replace \n with <br> for Plotly and only show labels for freq > 1
        labels = df['label'].where(df['freq'] > 1, '').fillna('').astype(str).str.lower().str.replace('\n', '<br>')
        text_size = 3 * (1 + size)
        
        # Implementa repel se richiesto
        if repel:
            # In Plotly non esiste un vero repel, ma possiamo aggiustare il posizionamento
            # Per una simulazione migliore si potrebbe implementare un algoritmo di repulsione
            fig.add_trace(go.Scatter(
                x=df['rcentrality'],
                y=df['rimpact'],
                text=labels,
                mode='text',
                textposition='top center',
                textfont=dict(size=text_size * 3),
                showlegend=False
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df['rcentrality'],
                y=df['rimpact'],
                text=labels,
                mode='text',
                textposition='middle center',
                textfont=dict(size=text_size * 3),
                showlegend=False
            ))

    # Calcola i limiti degli assi come in R
    if df.empty:
        xlimits = [0.0, 10.0]
        ylimits = [0.0, 10.0]
    else:
        df['rcentrality'] = df['rcentrality'].fillna(0.0)
        df['rimpact'] = df['rimpact'].fillna(0.0)
        
        xmin = df['rcentrality'].min()
        xmax = df['rcentrality'].max()
        ymin = df['rimpact'].min()
        ymax = df['rimpact'].max()
        
        rangex = max(meancentr - xmin, xmax - meancentr) if pd.notna(xmin) and pd.notna(xmax) else 1.0
        rangey = max(meandens - ymin, ymax - meandens) if pd.notna(ymin) and pd.notna(ymax) else 1.0
        
        if pd.isna(rangex) or rangex == 0: rangex = 1.0
        if pd.isna(rangey) or rangey == 0: rangey = 1.0

        xlimits = [meancentr - rangex - 0.5, meancentr + rangex + 0.5]
        ylimits = [meandens - rangey - 0.5, meandens + rangey + 0.5]
        
        # Guard against nan values
        xlimits = [0.0 if pd.isna(x) else x for x in xlimits]
        ylimits = [0.0 if pd.isna(y) else y for y in ylimits]

    # Aggiorna il layout del grafico per match con il tema di R
    fig.update_layout(
        showlegend=False,
        plot_bgcolor='white',
        xaxis=dict(
            title="Centrality",
            showgrid=False,
            showticklabels=False,
            showline=True,
            linewidth=0.5,
            linecolor='black',
            zeroline=False,
            range=xlimits
        ),
        yaxis=dict(
            title="Impact",
            showgrid=False,
            showticklabels=False,
            showline=True,
            linewidth=0.5,
            linecolor='black',
            zeroline=False,
            range=ylimits
        ),
        autosize=True,
        width=None,  # Let container control width
        height=None, # Let container control height if needed
    )

    g = fig
    df = df.rename(columns={'words': 'items'})

    params = {
        'analysis': analysis,
        'field': field,
        'n': n,
        'minfreq': minfreq,
        'label_term': label_term,
        'ngrams': ngrams,
        'impact_measure': impact_measure,
        'stemming': stemming,
        'n_labels': n_labels,
        'size': size,
        'community_repulsion': community_repulsion,
        'repel': repel
    }
    params = pd.DataFrame(list(params.items()), columns=['params', 'values'])

    # Clean any NaN values from return DataFrames to be completely JSON compliant in itables/Plotly
    df = df.fillna(0)
    df_lab = df_lab.fillna(0)
    D = D.fillna(0)
    params = params.fillna(0)

    results = {
        'map': g,
        'clusters': df,
        'data': df_lab,
        'nclust': len(df),
        'NCS': D,
        'net': Net,
        'params': params
    }
    return results


#### FUNCTION DA METTERE IN SERVICES???
# Normalizzazione del punteggio di citazione
def normalizeCitationScore(df, field="documents", impact_measure="local"):
    M = df.get() if hasattr(df, 'get') else df
    if field not in ["documents", "authors", "sources"]:
        print('\nfield argument is incorrect.\n\nPlease select one of the following choices: "documents", "authors", "sources"\n\n')
        return None

    # Applica localCitations se richiesto
    if impact_measure == "local":
        M = localCitations(df, fast_search=False, sep=";")['M']
    else:
        M['LCS'] = 0

    # Converte colonne in numerico
    M['TC'] = M['TC'].astype(float, errors='ignore')
    M['PY'] = M['PY'].astype(float, errors='ignore')

    # Rimpiazza LCS=0 con 1 e calcola NGCS/NLCS per anno
    M['LCS'] = M['LCS'].replace(0, 1)
    M['NGCS'] = M.groupby('PY')['TC'].transform(lambda x: x / x.mean(skipna=True))
    M['NLCS'] = M.groupby('PY')['LCS'].transform(lambda x: x / x.mean(skipna=True))

    # Suddivisione per tipo di campo richiesto
    if field == "documents":
        NCS = M[['SR', 'PY', 'NGCS', 'NLCS', 'TC', 'LCS']].rename(columns={
            'NGCS': 'MNGCS',
            'NLCS': 'MNLCS',
            'LCS': 'LC',
            'SR': 'documents'
        })

    elif field == "authors":
        # AU may already be a list (from ETL normalization) or a semicolon-delimited string
        M['AU'] = M['AU'].apply(
            lambda x: x if isinstance(x, list) else
                      [a.strip() for a in str(x).split(';') if a.strip()] if pd.notna(x) and str(x).strip() else []
        )
        exploded = M.explode('AU').assign(AU=lambda x: x['AU'].astype(str).str.strip())  # Espande e rimuove spazi extra
        exploded = exploded[exploded['AU'].notna() & (exploded['AU'] != '') & (exploded['AU'] != 'nan')]

        NCS = (
            exploded.groupby('AU').agg(
                NP=('PY', 'count'),
                MNGCS=('NGCS', 'mean'),
                MNLCS=('NLCS', 'mean'),
                TC=('TC', 'mean'),
                LC=('LCS', 'mean')
            )
            .reset_index()
            .rename(columns={'AU': 'authors'})
        )

    elif field == "sources":
        NCS = (
            M.groupby('SO').agg(
                NP=('PY', 'count'),
                MNGCS=('NGCS', 'mean'),
                MNLCS=('NLCS', 'mean'),
                TC=('TC', 'mean'),
                LC=('LCS', 'mean')
            )
            .reset_index()
            .rename(columns={'SO': 'sources'})
        )

    # Gestione impatto globale
    if impact_measure == "global":
        NCS.drop(columns=['MNLCS', 'LC'], errors='ignore', inplace=True)
    else:
        NCS['MNLCS'] = NCS['MNLCS'].fillna(0)

    return NCS# Network
def network(df, analysis, field, stemming, n, cluster, community_repulsion):
    NetMatrix = None  # Inizializza la matrice della rete
    
    # 1. Determine Coupling Unit field tag based on analysis type
    if analysis == "documents":
        unit_field = "SR"
    elif analysis == "authors":
        unit_field = "AU"
    elif analysis == "sources":
        unit_field = "SO"
    else:
        print(f"Unknown analysis type: {analysis}")
        return None

    # 2. Determine Coupling Attribute field tag based on coupling measure
    # If coupling measure is TI or AB, we perform term extraction first
    if field in ["TI", "AB"]:
        df = term_extraction(df, field=field, verbose=False, stemming=stemming)
        attr_field = f"{field}_TM"
    else:
        attr_field = field

    # 3. Compute generalized coupling
    print(f"[Coupling] Computing coupling network: Unit={unit_field}, Attribute={attr_field}")
    
    # Get Coupling Unit matrix WU (docs x units)
    WU = cocMatrix(df, Field=unit_field, type="sparse", n=None, sep=";", short=True)
    # Get Coupling Attribute matrix WA (docs x attributes)
    WA = cocMatrix(df, Field=attr_field, type="sparse", n=None, sep=";", short=True)
    
    if WU is not None and WA is not None and not WU.empty and not WA.empty:
        # Align index/rows of both matrices just in case
        common_idx = WU.index.intersection(WA.index)
        WU = WU.loc[common_idx]
        WA = WA.loc[common_idx]
        
        # Calculate cross product and coupling matrix
        # Compute: AU_matrix = WA.T @ WU (attributes x units)
        AU_matrix = WA.T @ WU
        # Compute: NetMatrix = AU_matrix.T @ AU_matrix (units x units)
        NetMatrix = AU_matrix.T @ AU_matrix
    else:
        print("[Coupling] Could not compute coupling network because one of the matrices is empty or None")
        NetMatrix = None
    
    # Controllo se la matrice è None (caso di errore o input non valido)
    if NetMatrix is None or NetMatrix.empty or NetMatrix.values.sum() == 0:
        print("\n\nNetwork matrix is empty!\nThe analysis cannot be performed\n\n")
        return None
    
    # Converti in DataFrame se non lo è già
    if not isinstance(NetMatrix, pd.DataFrame):
        NetMatrix = pd.DataFrame(NetMatrix)
    
    # Rimuovi colonne e righe con nomi vuoti
    NetMatrix = NetMatrix.loc[:, NetMatrix.columns.str.strip() != ""].loc[NetMatrix.index.str.strip() != ""]
    
    if NetMatrix.shape[0] > 0:
        Net = network_plot(NetMatrix, normalize="salton", n=n, 
                           Title=f"Coupling network of {analysis} using {field}", type="auto",
                           labelsize=2, halo=False, cluster=cluster, remove_isolates=True, 
                           community_repulsion=community_repulsion, remove_multiple=False, 
                           noloops=True, weighted=True, label_cex=True, edgesize=5, 
                           size=1, edges_min=1, label_n=n, verbose=False)
        return Net
    else:
        print("\n\nNetwork matrix is empty!\nThe analysis cannot be performed\n\n")
        return None


def labeling(df, df_lab, term, n, n_labels, analysis, ngrams):
    # Se il termine è TI o AB, estrai termini
    if term in ["TI", "AB"]:
        df = term_extraction(reactive.Value(df), field=term, ngrams=ngrams, verbose=False)
        df = df.get()
        term = f"{term}_TM"

    # Normalizzazione delle stringhe per evitare errori di merge
    df_lab = df_lab.apply(lambda x: x.astype(str).str.upper().str.strip())
    df = df.apply(lambda x: x.astype(str).str.upper().str.strip())

    # Analisi specifica
    if analysis == "documents":
        df = df_lab.merge(df, left_on="documents", right_on="SR", how="left")

    elif analysis == "authors":
        WF = cocMatrix(df, Field=term, short=True)
        WA = cocMatrix(df, Field="AU", n=n, short=True)

        if WA.shape[1] != WF.shape[0]:
            raise ValueError("Dimensioni non allineate tra WA e WF")

        AF = WA.T @ WF  # Prodotto matriciale

        # Creazione della mappa autore -> termini concatenati
        A = {
            author: ';'.join(
                [name for name, count in zip(WF.columns, AF[i].toarray().flatten()) if count > 0]
            )
            for i, author in enumerate(WA.columns)
        }
        
        A = pd.DataFrame(list(A.items()), columns=["AU", term])
        df = df_lab.merge(A, left_on="authors", right_on="AU", how="left")

    elif analysis == "sources":
        df = df_lab.merge(df, left_on="sources", right_on="SO", how="inner")

    # Se 'SR' non esiste, usa la prima colonna del DataFrame
    if 'SR' not in df.columns:
        df['SR'] = df.iloc[:, 0]

    # Creazione della tabella globale delle etichette
    df['SR'] = df.iloc[:, 0]
    tab_global = table_tag(df, term)
    tab_global = pd.DataFrame({
        'label': list(tab_global.keys()),
        'tot': list(tab_global.values()),
        'n': len(df)
    })

    # Assegnazione delle etichette migliori ai cluster
    df['w'] = df.groupby('Cluster').apply(lambda x: best_lab(x, tab_global, n_labels, term)).explode().reset_index(drop=True)

    return df['w']


def best_lab(df, tab_global, n_labels, term):
    # Creazione della tabella locale con le etichette
    tab = table_tag(df, term)
    tab = pd.DataFrame(list(tab.items()), columns=['label', 'value'])

    # Espandi le liste di parole nei singoli termini
    tab = tab.explode('label')

    # Merge con la tabella globale
    tab = tab.merge(tab_global, on='label', how="left")

    if tab.empty:
        return ""

    # Evita errori di divisione per zero
    tab['conf'] = round(tab['value'] / tab['tot'] * 100, 1).fillna(0)
    tab['supp'] = round(tab['tot'] / tab_global['n'].iloc[0] * 100, 1).fillna(0)
    tab['relevance'] = round(tab['conf'] * tab['supp'] / 100, 1)

    # Ordina per rilevanza e seleziona le migliori etichette
    tab = tab.sort_values(by='relevance', ascending=False).head(n_labels)

    # Ritorna la stringa con etichette e confidence
    return '\n'.join(f"{label} - conf {conf}%" for label, conf in zip(tab['label'], tab['conf'])).lower()


def localCitations(df, fast_search=False, sep=";"):
    df = metaTagExtraction(df, "SR") if hasattr(df, 'get') else df
    M = df.get() if hasattr(df, 'get') else df
    M['TC'] = M['TC'].fillna(0)
    if fast_search:
        loccit = M['TC'].quantile(0.75)
    else:
        loccit = 1
    
    H = histNetwork(df, min_citations=loccit, sep=sep, network=False)
    if H is None:
        # Fallback if histNetwork fails or is incompatible (e.g. Dimensions/WoS with no CR)
        M = M.copy()
        M['LCS'] = 0.0
        author_counts = pd.DataFrame(columns=["Authors", "N. of Local Citations"])
        if 'SR' in M.columns:
            LCS = M[['SR', 'DI', 'PY', 'LCS', 'TC']].rename(columns={
                'SR': 'Paper',
                'DI': 'DOI',
                'PY': 'Year',
                'LCS': 'LCS',
                'TC': 'GCS'
            })
        else:
            LCS = pd.DataFrame(columns=["Paper", "DOI", "Year", "LCS", "GCS"])
    else:
        LCS = H['histData']
        M = H['M']
        
        # Split authors and repeat local citations
        AU = M['AU'].explode()
        n = AU.groupby(level=0).size()
        
        # Create DataFrame for authors and local citations
        df_authors = pd.DataFrame({'AU': AU, 'LCS': M['LCS'].repeat(n).values})
        author_counts = df_authors.groupby('AU')['LCS'].sum().reset_index()
        author_counts.columns = ["Authors", "N. of Local Citations"]
        author_counts = author_counts.sort_values(by="N. of Local Citations", ascending=False)
        
        if 'SR' in M.columns:
            LCS = M[['SR', 'DI', 'PY', 'LCS', 'TC']].rename(columns={
                'SR': 'Paper',
                'DI': 'DOI',
                'PY': 'Year',
                'LCS': 'LCS',
                'TC': 'GCS'
            })
            LCS = LCS.sort_values(by='LCS', ascending=False)
    
    CR = {
        'Authors': author_counts,
        'Papers': LCS,
        'M': M
    }
    
    return CR


def adjust_color(color, alpha=0.5):
        """
        Adjust the color by changing its alpha value.
        """

        # Convert color to RGBA
        rgba = mcolors.to_rgba(color)
        # Adjust the alpha value
        adjusted_rgba = (rgba[0], rgba[1], rgba[2], alpha)
        # Convert back to hex
        return mcolors.to_hex(adjusted_rgba)

def avoid_net_overlaps(coords, labels, sizes, threshold=0.10):
    """Function to avoid label overlapping
    Args:
        coords: numpy array of x,y coordinates
        labels: list of node labels
        sizes: list of node sizes (dotSizes)
        threshold: distance threshold for overlap detection
    Returns:
        list of labels to remove to avoid overlap
    """
    
    # Create dataframe of nodes with labels
    df = pd.DataFrame({
        'x': coords[:, 0],
        'y': coords[:, 1] / 2,  # Normalize y coordinates
        'label': labels,
        'size': sizes
    })
    
    # Calculate pairwise manhattan distances
    distances = squareform(pdist(df[['x', 'y']], metric='cityblock'))
    
    # Create dataframe of overlapping pairs
    overlaps = []
    n = len(labels)
    for i in range(n):
        for j in range(i+1, n):
            if distances[i,j] < threshold:
                overlaps.append({
                    'from': labels[i],
                    'to': labels[j],
                    'dist': distances[i,j],
                    'w_from': sizes[i],
                    'w_to': sizes[j]
                })
    
    if not overlaps:
        return []
    
    # Convert to dataframe
    overlaps_df = pd.DataFrame(overlaps)
    
    labels_to_remove = []
    i = 0
    
    while len(overlaps_df) > 0:
        row = overlaps_df.iloc[0]
        
        if row['w_from'] > row['w_to'] and row['dist'] < threshold:
            label = row['to']
        elif row['w_from'] <= row['w_to'] and row['dist'] < threshold:
            label = row['from']
        else:
            overlaps_df = overlaps_df.iloc[1:]
            continue
        
        # Remove rows containing this label
        overlaps_df = overlaps_df[
            (overlaps_df['from'] != label) & 
            (overlaps_df['to'] != label)
        ]
        labels_to_remove.append(label)
    
    return labels_to_remove
