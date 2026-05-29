from www.services import *


def get_references_spectroscopy(df, start_year, end_year=2005, field_separator_spec=';'):
    """
    Generates a Reference Publication Year Spectroscopy (RPYS) interactive plot and tables from a DataFrame of bibliographic data.

    Args:
        df (pd.DataFrame): DataFrame containing bibliographic records with a 'CR' (cited references) column.
        start_year (int): Start year for the RPYS analysis.
        end_year (int, optional): End year for the RPYS analysis (default: 2005).
        field_separator_spec (str, optional): Field separator for references (default: ';').

    Returns:
        fig: Plotly interactive figure showing RPYS results.
        rpys_table (pd.DataFrame): Table with RPYS data (years, citations, deviation from median, top references).
        cr_table (pd.DataFrame): Table of cited references with local citation counts and Google Scholar links.
    """
    df = df.get()

    # Pulizia e preparazione dei dati
    c_references = df['CR'].apply(lambda x: [i for i in x]).explode()
    c_references = c_references.astype(str).str.replace('DOI;', 'DOI ')
    

    print(field_separator_spec)
    # Estrazione dei riferimenti
    references = c_references.str.split(f"{field_separator_spec}").apply(
        lambda x: [ref.strip() for ref in x if len(ref.strip()) > 10]
    )
    
    # Ripetere gli anni per ogni riferimento citato
    references_len = references.str.len()
    references = references[references_len > 0]
    cited_years = references.apply(lambda refs: [int(re.findall(r'\b\d{4},', ref)[0][:-1]) if re.findall(r'\b\d{4},', ref) else 0 for ref in refs]).explode().astype(int).reset_index(drop=True)
    references = references.explode().reset_index(drop=True)

    # Creazione del DataFrame delle citazioni
    ref_df = pd.DataFrame({'Reference': references, 'CitedYear': cited_years})

    # Filtraggio per intervallo temporale
    current_year = pd.Timestamp.now().year
    start_year = start_year if start_year is not None else 1700
    end_year = end_year if end_year is not None else current_year
    ref_df = ref_df[(ref_df['CitedYear'] >= start_year) & (ref_df['CitedYear'] <= end_year)]

    # Calcolo delle citazioni per anno
    cr_table = ref_df.groupby(['CitedYear', 'Reference']).size().reset_index(name='Freq')
    rpys_table = cr_table.groupby('CitedYear')['Freq'].sum().reset_index(name='Citations')

    # Aggiunta degli anni mancanti
    year_seq = rpys_table['CitedYear']
    if len(year_seq) == 0:
        # No references found in year range — return empty results
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text="No cited references found in the selected year range",
                            x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
            plot_bgcolor='white', height=300
        )
        fig = go.FigureWidget(fig)
        return fig, pd.DataFrame(), cr_table

    y_min = int(year_seq.min())
    y_max = int(year_seq.max())
    missing_years = set(range(y_min, y_max + 1)) - set(year_seq)
    missing_years_df = pd.DataFrame({'CitedYear': list(missing_years), 'Citations': [0] * len(missing_years)})
    rpys_table = pd.concat([rpys_table, missing_years_df]).sort_values('CitedYear').reset_index(drop=True)

    # Calcolo della mediana mobile
    YY = [0] * 4 + rpys_table['Citations'].tolist()
    Median = [np.median(YY[i - 4:i + 1]) for i in range(4, len(YY))]
    rpys_table['DiffMedian5'] = rpys_table['Citations'] - Median

    # Filtraggio per intervallo temporale
    rpys_table = rpys_table[(rpys_table['CitedYear'] >= start_year) & (rpys_table['CitedYear'] <= end_year)]

    # Imposta diffMedian a 0 se è negativo
    rpys_table['DiffMedian'] = rpys_table['DiffMedian5'].apply(lambda x: x if x > 0 else 0)

    # Identificazione dei top 3 riferimenti per anno
    top_references = cr_table.sort_values('Freq', ascending=False).groupby('CitedYear')['Reference'].apply(lambda refs: '\n'.join(refs)).reset_index()
    rpys_table = rpys_table.merge(top_references, left_on='CitedYear', right_on='CitedYear', how='left').rename(columns={'Reference': 'TopReferences'})
    rpys_table['TopReferences'] = rpys_table['TopReferences'].fillna('')

    # Creazione del grafico
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=rpys_table['CitedYear'], y=rpys_table['Citations'], mode='lines', name='Cited References', line=dict(color='#5567BB')),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=rpys_table['CitedYear'], y=rpys_table['DiffMedian'], mode='lines', name='Deviation from Median', line=dict(color='firebrick')),
        secondary_y=False,
    )

    fig.update_layout(
        xaxis_title='Year',
        yaxis_title='Cited References',
        plot_bgcolor='white',
        title_font_size=24,
        font=dict(color="#444444"),
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        height=600,
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    # Tabella CR con link Google Scholar
    cr_table['GoogleLink'] = cr_table['Reference'].apply(lambda ref: f'<a href="https://scholar.google.it/scholar?q={ref}" target="_blank">link</a>')
    cr_table = cr_table.rename(columns={'CitedYear': 'Year', 'Freq': 'Local Citations'})

    return fig, rpys_table, cr_table
