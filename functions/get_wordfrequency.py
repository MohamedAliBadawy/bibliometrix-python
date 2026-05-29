from www.services import *


def get_word_frequency(df, ngram, field_wf, file_upload_terms_wf, file_upload_synonyms_wf, occurrences, top_words):
    """
    Generate a plot of word frequency over time.

    Args:
        df: A DataFrame object containing the data.
        ngram: The number of n-grams to consider.
        field_wf: The field to analyze for word frequency.
        file_upload_terms_wf: File containing terms to remove.
        file_upload_synonyms_wf: File containing synonyms.
        occurrences: Type of occurrences ('cumulate' or 'per_year').
        top_words: The number of top words to display.

    Returns:
        A Plotly figure object representing the word frequency over time.
    """
    # Load terms to remove
    remove_terms = None
    if file_upload_terms_wf:
        with open(file_upload_terms_wf[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_terms = [line.strip() for line in file]

    # Load synonyms
    synonyms = None
    if file_upload_synonyms_wf:
        with open(file_upload_synonyms_wf[0]['datapath'], 'r', encoding='utf-8') as file:
            synonyms = {}
            for line in file:
                terms = [term.strip() for term in line.split(',')]
                key = terms[0]
                values = terms[1:]
                synonyms[key] = values

    # Set ngrams based on word_type
    ngrams = int(ngram) if field_wf in ['TI', 'AB'] else 1

    data = term_extraction(df, field=field_wf, stemming=False, verbose=False, 
                                ngrams=ngrams, remove_terms=remove_terms, synonyms=synonyms)
    data = data.get()
    
    # Calculate word frequency using the extracted tag column
    word_freq = keyword_growth(data, tag=f"{field_wf}_TM", top=top_words[1], cdf=(occurrences == 'cumulate'), remove_terms=remove_terms, synonyms=synonyms)


    # Select terms between top_words[1] and top_words[2]
    word_freq = word_freq[['Year'] + word_freq.columns[top_words[0]:top_words[1] + 1].tolist()]
    
    # Reshape the data for plotting
    word_freq_melted = word_freq.melt(id_vars=['Year'], var_name='Term', value_name='Frequency')

    # Create the plot
    fig = px.line(
        word_freq_melted,
        x='Year',
        y='Frequency',
        color='Term',
        labels={'Year': 'Year', 'Frequency': 'Frequency', 'Term': 'Term'},
    )

    # Customize the layout
    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=word_freq['Year'].unique()[::max(1, len(word_freq['Year'].unique()) // 20)]
        ),
        yaxis_title="Frequency",
        xaxis_title="Year",
        plot_bgcolor='white',
        title_font_size=24,
        font=dict(color="#444444"),
        margin=dict(l=40, r=40, t=40, b=40),
        height=800,
        legend=dict(
            title="Term",
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        )
    )

    # Customize the grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#EFEFEF')
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, word_freq

# Funzioni ausiliarie
def trim_years(w, year_range, cdf=True):
    """Funzione per calcolare frequenze cumulative o annuali."""
    W = np.zeros(len(year_range))
    Y = np.array(list(w.index))
    w_values = np.array(w)

    for i in range(len(year_range)):
        if len(Y) > 0 and Y[0] == year_range[i]:
            W[i] = w_values[0]
            Y = Y[1:]
            w_values = w_values[1:]

    if cdf:
        W = np.cumsum(W)

    W = pd.Series(W, index=year_range)

    return W


def keyword_growth(df, tag, sep=";", top=10, cdf=True, remove_terms=None, synonyms=None):
    """
    Simula la funzione KeywordGrowth in R.
    df: dataframe con i dati.
    tag: colonna da analizzare.
    sep: separatore per il parsing.
    top: numero massimo di termini da considerare.
    cdf: se True, calcola occorrenze cumulative.
    remove_terms: lista di termini da rimuovere.
    synonyms: dizionario {termine_sostituto: [lista_di_sinonimi]}.
    """
    # Parsing e filtraggio
    df = df.dropna(subset=[tag])
    df_tag_lists = df[tag].apply(lambda x: [i.strip() for i in str(x).split(sep) if i.strip()] if isinstance(x, str) else x if isinstance(x, (list, tuple, set)) else [])
    expanded = [str(item).upper() for sublist in df_tag_lists for item in sublist]
    years = df.loc[df.index.repeat(df_tag_lists.apply(len)), 'PY'].values
    data = pd.DataFrame({'Term': expanded, 'Year': years})
    
    # Rimuovi terms
    if remove_terms:
        data = data[~data['Term'].str.upper().isin([term.upper() for term in remove_terms])]
    
    # Gestione dei sinonimi
    if synonyms:
        for main_term, syns in synonyms.items():
            data['Term'] = data['Term'].replace(syns, main_term.upper())
    
    # Aggregazione
    freq = data.groupby(['Term', 'Year']).size().reset_index(name='Freq')
    # Filter out invalid years (<= 1800) to prevent chart starting at year 0
    freq = freq[freq['Year'] > 1800]
    if freq.empty:
        return pd.DataFrame(columns=['Year'])
    year_range = range(int(freq['Year'].min()), int(freq['Year'].max()) + 1)
    
    # Selezione dei termini più frequenti
    top_terms = freq.groupby('Term')['Freq'].sum().nlargest(top).index
    freq = freq[freq['Term'].isin(top_terms)]

    # Costruzione del dataframe finale
    results = pd.DataFrame({'Year': year_range})
    for term in top_terms:
        term_freq = freq[freq['Term'] == term].set_index('Year')['Freq']
        term_freq = term_freq.reindex(year_range, fill_value=0)
        results[term] = trim_years(term_freq, year_range, cdf=cdf).values

    return results
