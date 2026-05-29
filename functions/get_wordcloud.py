from www.services import *


def is_legible_on_white(color):
    """Restituisce True se il colore è leggibile su sfondo bianco"""
    r, g, b = mcolors.to_rgb(color)  # Converti in valori 0-1
    luminance = 0.299 * r + 0.587 * g + 0.114 * b  # Calcola la luminanza
    
    return 0.2 < luminance < 0.6  # Esclude colori troppo chiari o troppo scuri


def get_wordcloud(df, ngram, num_of_words_wc, field_wc, file_upload_terms_wc, file_upload_synonyms_wc):
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
    if file_upload_terms_wc:
        with open(file_upload_terms_wc[0]['datapath'], 'r', encoding='utf-8') as file:
            remove_terms = [line.strip() for line in file]

    synonyms = None
    if file_upload_synonyms_wc:
        with open(file_upload_synonyms_wc[0]['datapath'], 'r', encoding='utf-8') as file:
            synonyms = {}
            for line in file:
                terms = [term.strip() for term in line.split(',')]
                key = terms[0]
                values = terms[1:]
                synonyms[key] = values

    # Set ngrams based on word_type
    ngrams = int(ngram) if field_wc in ['TI', 'AB'] else 1

    # Get word counts
    words = table_tag(df, field_wc, ngrams, remove_terms, synonyms)

    # Create DataFrame of most frequent words
    word_counts = pd.DataFrame(words.items(), columns=['Words', 'Occurrences'])
    word_counts["Words"] = word_counts["Words"].str.capitalize()
    table = word_counts.sort_values(by='Occurrences', ascending=False)
    word_counts = word_counts.sort_values(by='Occurrences', ascending=False).head(num_of_words_wc)
    radius = 400

    word_frequencies = dict(zip(word_counts["Words"], word_counts["Occurrences"]))
    G = nx.Graph()
    
    colors = [c for c in mcolors.CSS4_COLORS.values() if is_legible_on_white(c)]
    
    sorted_words = sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True)
    center_word = sorted_words[0][0]  

    compact_radius = radius * 0.6

    # Calculate min and max counts to apply relative min-max scaling for pronounced font size contrast
    counts = [item[1] for item in sorted_words]
    max_count = max(counts) if counts else 1
    min_count = min(counts) if counts else 1
    count_range = max_count - min_count if max_count != min_count else 1

    for word, count in sorted_words:
        # Scale font size dynamically between 18 and 88 based on relative count
        norm_val = (count - min_count) / count_range
        font_size = int(18 + norm_val * 70)
        color = random.choice(colors)
        
        theta = random.uniform(0, 2 * math.pi)  
        r = compact_radius * math.sqrt(random.uniform(0, 1))  
        pos_x = r * math.cos(theta)
        pos_y = r * math.sin(theta)
        
        G.add_node(word, label=word, title=f"{word}: {count}", color="rgba(0,0,0,0)", 
                font={"size": font_size, "color": color, "strokeWidth": 1, "face": "Arial"}, x=pos_x, y=pos_y)

    # Creazione della rete interattiva con Pyvis
    g = Network(width="100%", height="98vh", bgcolor="white", font_color="black")
    g.from_nx(G)
    
    for n in g.nodes:
        n["font"] = {"size": G.nodes[n["id"]]["font"]["size"], "color": G.nodes[n["id"]]["font"]["color"], "strokeWidth": 1, "face": "Arial"}
        n["shape"] = "text"
    
    # Configure tight, compact Barnes-Hut physics to prevent text overlaps and keep words grouped close together
    g.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -800,
          "centralGravity": 0.75,
          "springLength": 30,
          "springConstant": 0.04,
          "damping": 0.09,
          "avoidOverlap": 1
        },
        "minVelocity": 0.5
      }
    }
    """)
    
    # Save the HTML file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    html_path = tmp.name
    with open(html_path, 'w', encoding="utf-8") as f:
        html = g.generate_html()
        new_css = "     .card {\n                 border: none;\n             }"
        updated_html = html.replace("</style>", new_css + "\n        </style>")
        updated_html = updated_html.replace("1px solid lightgray", "none")
        
        f.write(updated_html)
    
    return html_path.split(os.sep)[-1], table


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
