from .utils import *
from .termextraction import *


def table_tag(df, tag="CR", sep=";", ngrams=1, remove_terms=None, synonyms=None):
    """
    Extract and count words from a specified field in the DataFrame.
    """
    # Remove duplicates based on "SR"
    df = df.drop_duplicates(subset=["SR"])

    # Extract terms if tag is AB or TI
    if tag in ["AB", "TI"]:
        df = term_extraction(
            df,
            field=tag,
            stemming=False,
            verbose=False,
            ngrams=ngrams,
            remove_terms=remove_terms,
            synonyms=synonyms,
        )
        tag = f"{tag}_TM"

    # If the tag is "C1", remove text within square brackets
    if tag == "C1":
        df[tag] = df[tag].apply(
            lambda x: re.sub(r"\[.+?\]", "", x) if isinstance(x, str) else x
        )

    # Convert each string to a list using ast.literal_eval or splitting by separator
    def parse_to_list(val):
        if isinstance(val, (list, tuple, set)):
            return val
        if isinstance(val, str):
            val_stripped = val.strip()
            if not val_stripped:
                return []
            if (val_stripped.startswith('[') and val_stripped.endswith(']')) or \
               (val_stripped.startswith('(') and val_stripped.endswith(')')):
                try:
                    res = ast.literal_eval(val_stripped)
                    if isinstance(res, (list, tuple, set)):
                        return res
                except (ValueError, SyntaxError):
                    pass
            return [i.strip() for i in val.split(sep) if i.strip()]
        return []

    df[tag] = df[tag].apply(parse_to_list)

    # Create a unique list of all words in a float-safe way
    all_words = []
    for sublist in df[tag]:
        if isinstance(sublist, (list, tuple, set)):
            for word in sublist:
                if isinstance(word, (str, bytes)):
                    all_words.append(str(word))
        elif isinstance(sublist, str) and sublist:
            all_words.append(sublist)

    # Clean text (remove extra spaces, isolated periods and commas)
    words = [
        re.sub(r"\s+|[.,]", " ", word).strip().upper()
        for word in all_words
        if word.strip()
    ]

    # Replace synonyms
    if synonyms:
        synonym_map = {}
        for s in synonyms:
            terms = s.split(";")
            main_term = terms[0].upper()
            for alt in terms[1:]:
                synonym_map[alt.upper()] = main_term
        words = [synonym_map.get(word, word) for word in words]

    # Count occurrences
    word_counts = Counter(words)

    # Remove specified terms
    if remove_terms and tag in ["DE", "ID"]:
        remove_set = set(term.upper() for term in remove_terms)
        word_counts = {
            word: count for word, count in word_counts.items() if word not in remove_set
        }

    return dict(sorted(word_counts.items(), key=lambda item: item[1], reverse=True))
