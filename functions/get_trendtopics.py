from www.services import *


def get_trend_topics(df, ngram, field_tt, time_window, file_upload_terms_tt, file_upload_synonyms_tt, word_minimum_frequency, number_of_words_year):
    """
    Generate a plot of trend topics over time.

    Args:
        df: A DataFrame object containing the data.
        ngram: The number of n-grams to consider.
        field_tt: The field to analyze for trend topics.
        time_window: The time window to consider.
        file_upload_terms_tt: File containing terms to remove.
        file_upload_synonyms_tt: File containing synonyms.
        word_minimum_frequency: The minimum frequency of words to consider.
        number_of_words_year: The number of words to display per year.

    Returns:
        A Plotly figure object representing the trend topics over time.
    """
    
    # Load terms to remove
    remove_terms = None
    if file_upload_terms_tt:
        with open(file_upload_terms_tt[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_terms = [line.strip() for line in file]

    # Load synonyms
    synonyms = None
    if file_upload_synonyms_tt:
        with open(file_upload_synonyms_tt[0]['datapath'], 'r', encoding='utf-8') as file:
            synonyms = {}
            for line in file:
                terms = [term.strip() for term in line.split(',')]
                key = terms[0]
                values = terms[1:]
                synonyms[key] = values

    # Set ngrams based on word_type
    ngrams = int(ngram) if field_tt in ['TI', 'AB'] else 1

    # Extract terms unconditionally
    df = term_extraction(df, field=field_tt, stemming=False, verbose=False, 
                         ngrams=ngrams, remove_terms=remove_terms, synonyms=synonyms)
    field = f"{field_tt}_TM"

    # Get trend topics
    trend_topics = field_by_year(df, field, time_window, word_minimum_frequency, number_of_words_year, remove_terms, synonyms)

    # Handle empty results
    if len(trend_topics) == 0:
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text="No trend topics found for the selected parameters",
                            x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
            plot_bgcolor='white', height=300
        )
        fig = go.FigureWidget(fig)
        return fig, trend_topics

    # Linear min-max scaling for marker sizes to guarantee beautiful visual contrast without microscopic dots
    min_f = trend_topics['freq'].min()
    max_f = trend_topics['freq'].max()
    f_range = max_f - min_f if max_f != min_f else 1
    trend_topics['scaled_size'] = 10 + ((trend_topics['freq'] - min_f) / f_range) * 22

    # Plot
    fig = px.scatter(
        trend_topics, 
        x='year_med', 
        y='item', 
        size='scaled_size', 
        hover_data=['year_q1', 'year_q3'], 
        height=800,
        color_discrete_sequence=['dodgerblue']
    )
    fig.update_layout(
        xaxis_title='Year', 
        yaxis_title='Term', 
        showlegend=False, 
        plot_bgcolor='white',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='lightgrey'),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),
    )
    fig.update_traces(
        hovertemplate=
            "<b>Term:</b> %{y}<br>" +
            "<b>Median Year:</b> %{x}<br>" +
            "<b>Frequency:</b> %{customdata[2]}<br>" +
            "<b>Q1 Year:</b> %{customdata[0]}<br>" +
            "<b>Q3 Year:</b> %{customdata[1]}<br>" +
            "<extra></extra>",
        customdata=trend_topics[['year_q1', 'year_q3', 'freq']].values
    )

    for i in range(len(trend_topics)):
        fig.add_shape(
            type='line',
            x0=trend_topics['year_q1'].iloc[i], 
            y0=i,
            x1=trend_topics['year_q3'].iloc[i], 
            y1=i,
            line=dict(color='lightblue', width=5),  # Adjust width proportionally
            layer='below'
        )

    # Safely apply precise diameter sizing and set opacity
    fig.update_traces(
        marker=dict(
            sizemode='diameter',
            sizeref=1.0,
            opacity=1.0
        ), 
        selector=dict(mode='markers')
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, trend_topics

def field_by_year(df, field, timespan, min_freq, n_items, remove_terms=None, synonyms=None):
    # Create co-occurrence matrix
    A = cocMatrix(df, Field=field, binary=False, remove_terms=remove_terms, synonyms=synonyms)

    # Handle empty matrix
    if A is None or A.shape[1] == 0:
        return pd.DataFrame(columns=['year_q1', 'year_med', 'year_q3', 'freq', 'item'])

    n = A.sum(axis=0).to_numpy()  # Convert to 1D array
    df = df.get()

    # Calculate quantiles
    trend_med = pd.DataFrame(A.values).apply(lambda x: pd.Series(np.round(np.quantile(np.repeat(df['PY'], x), [0.25, 0.5, 0.75]))), axis=0).T
    trend_med.columns = ['year_q1', 'year_med', 'year_q3']
    trend_med['freq'] = n
    trend_med['item'] = A.columns

    # Handle timespan: can be None, an int (window size), or a 2-element list
    if timespan is None or (isinstance(timespan, (int, float)) and not hasattr(timespan, '__len__')):
        max_year = trend_med['year_med'].max()
        if isinstance(timespan, (int, float)) and timespan > 0:
            min_year = max_year - int(timespan)
        else:
            min_year = trend_med['year_med'].min()
        timespan = [min_year, max_year]
    elif hasattr(timespan, '__len__') and len(timespan) != 2:
        timespan = [trend_med['year_med'].min(), trend_med['year_med'].max()]

    trend_med = trend_med[(trend_med['year_med'] >= timespan[0]) & (trend_med['year_med'] <= timespan[1])]
    trend_med = trend_med[trend_med['freq'] >= min_freq]

    if len(trend_med) == 0:
        return pd.DataFrame(columns=['year_q1', 'year_med', 'year_q3', 'freq', 'item'])

    trend_med = trend_med.groupby('year_med').apply(lambda x: x.nlargest(n_items, 'freq')).reset_index(drop=True)

    return trend_med

