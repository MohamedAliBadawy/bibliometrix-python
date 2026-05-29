from .utils import *


def cocMatrix(df, Field="AU", type="sparse", n=None, sep=";", binary=True, short=False, remove_terms=None, synonyms=None):
    """
    Computes occurrences between elements of a Tag Field from a bibliographic data frame.
    
    Args:
        M: A DataFrame obtained by the converting function. It is a data matrix with cases corresponding to articles and variables to Field Tag in the original WoS or SCOPUS file.
        Field: A string indicating one of the field tags of the standard ISI WoS Field Tag codify.
        type: Indicates the output format of co-occurrences ("matrix" or "sparse").
        n: An integer indicating the number of items to select. If None, all items are selected.
        sep: The field separator character.
        binary: A boolean. If True each cell contains a 0/1. If False each cell contains the frequency.
        short: A boolean. If True all items with frequency < 2 are deleted to reduce the matrix size.
        remove_terms: A list of additional terms to delete from the documents before term extraction.
        synonyms: A list of synonyms that will be merged into a single term.
        
    Returns:
        A bipartite network matrix with cases corresponding to manuscripts and variables to the objects extracted from the Tag Field.
    """
    M = df.get()

    if "LABEL" not in M.columns:
        M.index = M["SR"]
        print("Processing field: " + Field + "\n")
    RowNames = M.index

    # REMOVE TERMS AND MERGE SYNONYMS
    if Field in ["ID", "DE", "TI", "TI_TM", "AB", "AB_TM"]:
        Fi = M[Field].fillna("").apply(lambda x: x if isinstance(x, list) else [i.strip() for i in x.split(sep)])
        TERMS = pd.DataFrame({"item": [item.upper() for sublist in Fi for item in sublist], "SR": M.index.repeat(Fi.str.len())})

        # Merge synonyms
        if synonyms:
            synonyms_dict = {syn.split(";")[0].strip().upper(): [s.strip().upper() for s in syn.split(";")[1:]] for syn in synonyms}
            for key, values in synonyms_dict.items():
                TERMS["item"] = TERMS["item"].replace(values, key)

        # Remove terms
        if remove_terms:
            TERMS = TERMS[~TERMS["item"].str.upper().isin([term.strip().upper() for term in remove_terms])]

        TERMS = TERMS.groupby("SR")["item"].apply(lambda x: ";".join(x)).reset_index()
        M = M.drop(columns=[Field, 'SR']).merge(TERMS, on="SR", how="left").rename(columns={"item": Field})
        M.index = RowNames

    if Field == "CR":
        M["CR"] = M["CR"].apply(
            lambda x: [str(ref).replace("DOI;", "DOI ") for ref in x if pd.notna(ref)] 
            if isinstance(x, (list, tuple, set)) else x
        )

    if Field in M.columns:
        Fi = M[Field].fillna("").apply(
            lambda x: x if isinstance(x, (list, tuple, set)) else 
                      [i.strip() for i in str(x).split(sep) if i.strip()] if pd.notna(x) and str(x).strip() else []
        )
    else:
        print(f"Field {Field} is not a column name of input data frame")
        return

    Fi = Fi.apply(lambda x: [str(i).strip() for i in x] if isinstance(x, (list, tuple, set)) else [])
    if Field == "CR":
        Fi = Fi.apply(lambda x: [i for i in x if isinstance(i, str) and len(i) > 10] if isinstance(x, (list, tuple, set)) else [])

    allField = [item for sublist in Fi for item in sublist if item]
    if Field == "CR":
        allField = reduceRefs(allField)
        Fi = Fi.apply(reduceRefs)

    tabField = pd.Series(allField).value_counts()
    uniqueField = tabField.index.tolist()

    if n:
        uniqueField = uniqueField[:n]
    elif short and Field != "SR":
        uniqueField = tabField[tabField > 1].index.tolist()

    if not uniqueField:
        print("Matrix is empty!!")
        return None

    if type == "matrix" or not binary:
        WF = np.zeros((M.shape[0], len(uniqueField)))
    elif type == "sparse":
        WF = lil_matrix((M.shape[0], len(uniqueField)))
    else:
        print("Error in type argument")
        return

    col_idx = {term: idx for idx, term in enumerate(uniqueField)}
    row_idx = {sr: idx for idx, sr in enumerate(M.index)}

    for i, terms in Fi.items():
        if terms:
            if binary:
                indices = [col_idx[term] for term in set(terms) if term in col_idx]
                WF[row_idx[i], indices] = 1
            else:
                term_counts = pd.Series(terms).value_counts()
                for term, count in term_counts.items():
                    if term in col_idx:
                        WF[row_idx[i], col_idx[term]] = count

    if type == "sparse" and not binary:
        WF = lil_matrix(WF)

    # Convert the sparse matrix to a DataFrame for better readability
    WF_df = pd.DataFrame(WF.toarray(), index=M.index, columns=uniqueField)
    if binary:
        WF_df = WF_df.astype(int)  # Ensure binary values are 0 and 1
    # print(WF_df)

    return WF_df


def reduceRefs(refs):
    """
    Remove everything after "V" followed by a digit and "DOI " from references.

    Args:
        refs: A list of references to reduce.

    Returns:
        A list of reduced references.
    """
    if not isinstance(refs, (list, tuple, set)):
        return []
    reduced_refs = []
    for ref in refs:
        if not isinstance(ref, str):
            continue
        # Remove everything after "V" followed by a digit
        v_match = re.search(r"V\d", ref)
        if v_match:
            ref = ref[:v_match.start()]
        
        # Remove everything after "DOI "
        doi_match = re.search(r"DOI ", ref)
        if doi_match:
            ref = ref[:doi_match.start()]
        
        reduced_refs.append(ref.strip())

    return reduced_refs
