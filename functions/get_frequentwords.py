from www.services import *


def get_frequent_words(df, ngram, num_of_words, word_type, file_upload_terms, file_upload_synonyms, field_separator_frequent=';'):
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

    # Create plot
    fig = px.scatter(
        word_counts,
        x="Occurrences",
        y="Words",
        text="Occurrences",
        size="Occurrences",
        size_max=60,
        color="Occurrences",
        color_continuous_scale=[(0, "lightblue"), (1, "darkblue")]
    )

    # Customize traces
    fig.update_traces(
        marker=dict(opacity=1, size=word_counts["Occurrences"]),
        textposition="middle center",
        textfont=dict(color="white", size=12)
    )

    # Add horizontal lines
    for _, row in word_counts.iterrows():
        fig.add_shape(
            type="line",
            x0=0,
            y0=row["Words"],
            x1=row["Occurrences"],
            y1=row["Words"],
            line=dict(color="LightGrey", width=3),
            layer="below"
        )

    # Update layout
    fig.update_layout(
        yaxis=dict(autorange="reversed", showgrid=True, gridcolor="lightgrey", zeroline=False),
        xaxis=dict(showgrid=True, gridcolor="lightgrey", zeroline=False),
        plot_bgcolor='white',
        font=dict(color="#444444"),
        margin=dict(l=0, r=0, t=0, b=0),
        height=50 + 90 * len(word_counts),
        coloraxis_showscale=False,
        showlegend=False,
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),
    )

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
