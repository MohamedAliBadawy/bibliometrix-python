from .utils import *


def term_extraction(df, field="TI", ngrams=1, stemming=False, language="english", remove_numbers=True, remove_terms=None, keep_terms=None, synonyms=None, verbose=False):
    """
    Extract terms from a specified field in the DataFrame.

    Args:
        df: A DataFrame object containing the data.
        field: The field from which to extract terms.
        ngrams: The number of n-grams to extract.
        stemming: Whether to apply stemming.
        language: The language for stopwords and stemming.
        remove_numbers: Whether to remove numbers.
        remove_terms: Terms to remove from the text.
        keep_terms: Terms to keep in the text.
        synonyms: Synonyms to merge into a single term.
        verbose: Whether to print the results.

    Returns:
        A DataFrame with the extracted terms.
    """
    M = df.get()
    overall_start_time = time.time()

    # Load and update stopwords
    stop_words = set(nltk_stopwords.words(language))
    r_stopwords = {"elsevier", "springer", "wiley", "mdpi", "emerald", "originalityvalue", "designmethodologyapproach",
                   "-", " -", "-present", "-based", "-literature", "-matter"}
    stop_words.update(r_stopwords)

    if field in ["ID", "DE"]:
        # ngrams is forced to 1 for keywords in R's termExtraction
        ngrams = 1

        processed_docs = []
        for val in M[field]:
            if not isinstance(val, list):
                if pd.isna(val) or val is None or str(val) == "":
                    processed_docs.append([])
                    continue
                # Split by semicolon if it's a string
                val = [item.strip() for item in str(val).split(";") if item.strip()]
            
            # For each keyword, replace - with __ and space with _
            doc_terms = []
            for term in val:
                t = str(term).strip()
                if t and t not in ("", "nan", "None"):
                    t = t.lower()
                    if remove_numbers:
                        t = re.sub(r"\d+", "", t)
                    t = t.replace("-", "__").replace(" ", "_")
                    doc_terms.append(t)
            processed_docs.append(doc_terms)
        
        final_docs = []
        for doc in processed_docs:
            doc_terms = []
            for term in doc:
                # Restore original format for stopword checking and stemming
                restored = term.replace("__", "-").replace("_", " ")
                
                # Improved/Correct Stopword Filtering:
                # We only filter out the keyword if the entire phrase itself is a stopword
                if restored.lower() in stop_words:
                    continue
                
                if stemming:
                    stemmer = SnowballStemmer(language)
                    words = [stemmer.stem(w) for w in words]
                    restored = " ".join(words)
                
                restored = restored.upper()
                
                custom_stopngrams = {
                    "RIGHTS RESERVED", "JOHN WILEY", "JOHN WILEY SONS", "SCIENCE BV", "MDPI BASEL",
                    "MDPI LICENSEE", "EMERALD PUBLISHING", "TAYLOR FRANCIS", "PAPER PROPOSES",
                    "WE PROPOSES", "PAPER AIMS", "ARTICLES PUBLISHED", "STUDY AIMS", "RESEARCH LIMITATIONSIMPLICATIONS"
                }
                if remove_terms:
                    custom_stopngrams.update([term.upper() for term in remove_terms])
                
                if restored in custom_stopngrams or restored == "":
                    continue
                
                # Synonyms merge
                if synonyms:
                    matched_key = None
                    for key, syn_list in synonyms.items():
                        if restored in [s.upper() for s in syn_list]:
                            matched_key = key.upper()
                            break
                    if matched_key:
                        restored = matched_key
                
                doc_terms.append(restored)
            final_docs.append(doc_terms)
        
        M[f"{field}_TM"] = final_docs
        df.set(M)
        return df

    # Original CountVectorizer path for TI and AB fields
    stop_words_list = list(stop_words)
    M[f"{field}_TM"] = M[field].astype(str).str.lower()
    M[f"{field}_TM"] = M[f"{field}_TM"].str.replace(r"[^a-z\s-]", " ", regex=True)
    M[f"{field}_TM"] = M[f"{field}_TM"].str.replace("-", "__")

    if remove_numbers:
        M[f"{field}_TM"] = M[f"{field}_TM"].str.replace(r"\d+", "", regex=True)

    if keep_terms:
        keep_terms = [term.lower().replace(" ", "_").replace("-", "__") for term in keep_terms]
        for term in keep_terms:
            M[f"{field}_TM"] = M[f"{field}_TM"].str.replace(term.replace(" ", "_"), term)

    if remove_terms:
        remove_terms = [term.lower() for term in remove_terms]
        for term in remove_terms:
            M[f"{field}_TM"] = M[f"{field}_TM"].str.replace(term, "")

    if stemming:
        stemmer = SnowballStemmer(language)
        M[f"{field}_TM"] = M[f"{field}_TM"].apply(lambda x: " ".join([stemmer.stem(word) for word in x.split()]))

    vectorizer = CountVectorizer(ngram_range=(ngrams, ngrams), stop_words=stop_words_list, token_pattern=r"(?u)\b\w\w+\b")
    X = vectorizer.fit_transform(M[f"{field}_TM"])
    terms = vectorizer.get_feature_names_out()

    if synonyms:
        synonyms_dict = {key.lower(): [s.lower() for s in values] for key, values in synonyms.items()}
        terms = [next((k for k, v in synonyms_dict.items() if term in v), term) for term in terms]

    terms_df = pd.DataFrame(X.toarray(), columns=terms, index=M.index)

    start_time = time.time()
    non_zero_mask = terms_df.values > 0
    extracted_terms = [
        [terms_df.columns[i].replace("__", "-").replace("_", " ").replace("-", " ")
         for i in np.where(non_zero_mask[row_idx])[0]]
        for row_idx in range(non_zero_mask.shape[0])
    ]

    M[f"{field}_TM"] = extracted_terms
    print(f"Term combination into lists per document done in {time.time() - start_time:.4f} seconds")

    if verbose:
        print(terms_df.sum().sort_values(ascending=False).head(25))

    df.set(M)
    return df
