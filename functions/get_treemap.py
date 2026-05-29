from www.services import *


def get_treemap(df, ngram, num_of_words, word_type, file_upload_terms, file_upload_synonyms, field_separator_frequent=';'):
    """
    Generate a plot and table of the most frequent words.
    
    Args:
        df: A DataFrame object containing the data.
        num_of_words: The number of top frequent words to display.
        word_type: The type of words to analyze (e.g., 'TI', 'AB').
        field_separator_frequent: The separator used in the field.
        file_upload_terms: File containing terms to remove.
        file_upload_synonyms: File containing synonyms.
        
    Returns:
        A Plotly figure object and a DataFrame of the most frequent words.
    """

    # Load stopwords and synonyms
    remove_terms = None
    if file_upload_terms:
        with open(file_upload_terms[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_terms = [line.strip() for line in file]

    synonyms = None
    if file_upload_synonyms:
        with open(file_upload_synonyms[0]['datapath'], 'r', encoding='utf-8') as file:
            synonyms = {}
            for line in file:
                terms = [term.strip() for term in line.split(',')]
                key = terms[0]
                values = terms[1:]
                synonyms[key] = values

    # Set ngrams based on word_type
    ngrams = int(ngram) if word_type in ['TI', 'AB'] else 1
    print(ngrams)

    # Get word counts
    words = table_tag(df, word_type, ngrams, remove_terms, synonyms)

    # Create DataFrame of most frequent words
    word_counts = pd.DataFrame(words.items(), columns=['Words', 'Occurrences'])
    table = word_counts.sort_values(by='Occurrences', ascending=False)
    word_counts = word_counts.sort_values(by='Occurrences', ascending=False).head(num_of_words)

    # Create TreeMap plot
    fig = px.treemap(
        word_counts,
        path=[px.Constant("Tree"), 'Words'],
        values='Occurrences',
        color='Occurrences',
        color_continuous_scale=[(0, "lightblue"), (1, "darkblue")],
    )

    # Update layout
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        height=800,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )

    # Add text to each cell
    fig.data[0].texttemplate = "%{label}<br>%{value} Occurrences<br>%{percentParent:.2%}"
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    return fig, table

def table_tag(df, tag, ngrams=1, remove_terms=None, synonyms=None):
    """
    Extract and count words from a specified field in the DataFrame.
    """
    M = df.get()
    
    # Remove duplicates
    M = M.drop_duplicates(subset='SR')
    
    # Get text data unconditionally
    text_data = term_extraction(df, field=tag, stemming=False, verbose=False, 
                                ngrams=ngrams, remove_terms=remove_terms, synonyms=synonyms)
    text_data = text_data.get()
    text_data = text_data[f"{tag}_TM"]

    # Process words in a float-safe way (since all fields now yield a list of lists of terms)
    words = []
    for sublist in text_data:
        if isinstance(sublist, (list, tuple, set)):
            for item in sublist:
                if isinstance(item, (str, bytes)):
                    words.append(str(item))
        elif isinstance(sublist, str) and sublist:
            words.append(sublist)

    # Apply n-grams if needed
    # if ngrams > 1 and tag not in ['DE', 'ID']:
    #     words = [' '.join(words[i:i+ngrams]) for i in range(len(words)-ngrams+1)]

    # Replace synonyms
    if synonyms:
        for key, syn_list in synonyms.items():
            words = [key if word in syn_list else word for word in words]

    # Count words
    word_counts = Counter(words)

    # Remove specified terms
    if remove_terms and tag in ['DE', 'ID']:
        word_counts = {word: count for word, count in word_counts.items() 
                      if word.upper() not in [term.upper() for term in remove_terms]}

    return word_counts
