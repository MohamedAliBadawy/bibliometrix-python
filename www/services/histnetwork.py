from .utils import *
from .cocmatrix import *


def histNetwork(df, min_citations=0, sep=";", network=True):
    """
    Create a historical network of citations from a DataFrame containing metadata of scientific papers.
    
    Args:
        df (DataFrame): A DataFrame containing metadata of scientific papers.
        min_citations (int): Minimum number of citations to include a paper in the analysis.
        sep (str): Separator used to separate references in the citation network.
        network (bool): If True, a citation network is created.
    
    Returns:
        A dictionary containing the following keys:
            - NetMatrix: A DataFrame containing the citation network.
            - histData: A DataFrame containing the metadata of the papers.
            - M: A DataFrame containing the metadata of the papers with the Local Citation Score (LCS).
            - LCS: A list containing the Local Citation Score of each paper.
    """
    M = df.get() if hasattr(df, 'get') else df
    db = M['DB'].iloc[0] if hasattr(M['DB'], 'iloc') else M['DB'][0]

    # Ensure required fields are present
    if 'DI' not in M:
        M['DI'] = ""
    M['DI'] = M['DI'].fillna("")

    if 'CR' not in M:
        print("\nYour collection does not contain Cited References metadata (Field CR is missing)\n")
        return None

    # Fill missing values in TC
    M['TC'] = M['TC'].fillna(0)

    if db.lower() in ("web_of_science", "web of science", "wos", "isi"):
        results = wos(M, min_citations=min_citations, sep=sep, network=network)
    elif db.lower() == "scopus":
        results = scopus(M, min_citations=min_citations, sep=sep, network=network)
    elif db.lower() == "lens":
        results = lens(M, min_citations=min_citations, sep=sep, network=network)
    else:
        print("\nDatabase not compatible with direct citation analysis\n")
        return None

    return results


def wos(M, min_citations, sep, network):

    print("\nWOS DB:\nSearching local citations (LCS) by reference items (SR) and DOIs...\n")

    # Sort data by publication year
    M = M.sort_values(by="PY").reset_index(drop=True)

    # Add unique labels to papers
    M['Paper'] = np.arange(0, len(M))
    M['nLABEL'] = np.arange(0, len(M))

    # Process cited references (CR)
    CR = []
    for i, refs in enumerate(M['CR']):
        for ref in refs:
            # Extract DOI
            doi = ""
            if 'DOI' in ref:
                parts = ref.split('DOI', 1)
                doi = parts[1].strip() if len(parts) > 1 else ""
            # Extract AU, PY, SO
            ref_parts = ref.split(',')
            au = ref_parts[0].replace('.', ' ').strip() if len(ref_parts) > 0 else ""
            py = ref_parts[1].strip() if len(ref_parts) > 1 else ""
            so = ref_parts[2].strip() if len(ref_parts) > 2 else ""
            sr = f"{au}, {py}, {so}"
            CR.append({'ref': ref, 'Paper': i, 'DI': doi, 'AU': au, 'PY': py, 'SO': so, 'SR': sr})

    print(f"\nAnalyzing {len(CR)} reference items...\n")

    CR_df = pd.DataFrame(CR)

    # Ensure DI and SR fields are stripped and upper-cased for matching
    M['LABEL'] = M['SR_FULL'].fillna('').str.upper().str.strip()
    CR_df['LABEL'] = CR_df['SR'].fillna('').str.upper().str.strip()
    
    M['DI_clean'] = M['DI'].fillna('').str.upper().str.strip()
    CR_df['DI_clean'] = CR_df['DI'].fillna('').str.upper().str.strip()
    
    M['SR_clean'] = M['SR_FULL'].fillna('').str.upper().str.replace(r'\s+', ' ', regex=True).str.strip()
    CR_df['SR_clean'] = CR_df['SR'].fillna('').str.upper().str.replace(r'\s+', ' ', regex=True).str.strip()
    
    # Match by DOI (only when DOI is not empty on both sides)
    M_doi = M[M['DI_clean'] != ''].copy()
    CR_df_doi = CR_df[CR_df['DI_clean'] != ''].copy()
    L_doi = pd.merge(M_doi, CR_df_doi, on='DI_clean', suffixes=('_M', '_CR')) if len(M_doi) > 0 and len(CR_df_doi) > 0 else pd.DataFrame()
    
    # Match by Short Reference (SR)
    M_sr = M[M['SR_clean'] != ''].copy()
    CR_df_sr = CR_df[CR_df['SR_clean'] != ''].copy()
    L_sr = pd.merge(M_sr, CR_df_sr, on='SR_clean', suffixes=('_M', '_CR')) if len(M_sr) > 0 and len(CR_df_sr) > 0 else pd.DataFrame()
    
    # Align and concatenate matched results
    common_cols = list(set(L_doi.columns) & set(L_sr.columns)) if not L_doi.empty and not L_sr.empty else list(L_sr.columns) if not L_sr.empty else list(L_doi.columns) if not L_doi.empty else []
    
    if common_cols:
        L_list = []
        if not L_doi.empty:
            L_list.append(L_doi[common_cols])
        if not L_sr.empty:
            L_list.append(L_sr[common_cols])
        L = pd.concat(L_list).drop_duplicates(subset=['nLABEL', 'Paper_CR'])
    else:
        L = pd.DataFrame(columns=['nLABEL', 'Paper_CR', 'LABEL'])
    
    L['Paper_CR'] = L['Paper_CR'].astype(int)
    L['CITING'] = M.loc[L['Paper_CR'], 'LABEL'].values
    L['nCITING'] = M.loc[L['Paper_CR'], 'nLABEL'].values
    L['CIT_PY'] = M.loc[L['Paper_CR'], 'PY'].values

    # Compute Local Citation Scores (LCS)
    LCS = L.groupby('nLABEL').size().reset_index(name='LCS')
    M['LCS'] = M['nLABEL'].map(LCS.set_index('nLABEL')['LCS']).fillna(0).astype(int)

    # Prepare histData
    histData = M[M['TC'] >= min_citations][['LABEL', 'TI', 'DE', 'ID', 'DI', 'PY', 'LCS', 'TC']]
    histData.columns = ['Paper', 'Title', 'Author_Keywords', 'KeywordsPlus', 'DOI', 'Year', 'LCS', 'GCS']

    WLCR = None
    if network:
        # Build citation network
        CITING = L.groupby('CITING').agg(
            LCR=('LABEL_M', lambda x: ';'.join(x.dropna())),
            PY=('CIT_PY', 'first'),
            Paper=('Paper_CR', 'first')
        ).reset_index().sort_values(by='PY')

        # Assign LCR to the correct Paper index (Paper is 0-based)
        M['LCR'] = ""
        for idx, row in CITING.iterrows():
            paper_idx = int(row['Paper'])
            if 0 <= paper_idx < len(M):
                M.at[paper_idx, 'LCR'] = row['LCR']

        # Assign unique names to duplicated LABELs
        st = False
        i = 0
        while not st:
            ind = M['LABEL'].duplicated(keep=False)
            if ind.any():
                i += 1
                M.loc[ind, 'LABEL'] = M.loc[ind, 'LABEL'] + f"-{chr(96 + i)}"
            else:
                st = True
        M.index = M['LABEL'].str.strip()

        M['LCR'] = M['LCR'].fillna('')

        # Ensure all papers are included as both rows and columns
        WLCR = cocMatrix(reactive.Value(M), Field="LCR", sep=sep)
        
        # Trova le LABEL mancanti
        missing_LABEL = set(M.index) - set(WLCR.columns)
        
        # Aggiungi colonne per le LABEL mancanti con valori 0 (in un'unica operazione per evitare frammentazione)
        if missing_LABEL:
            missing_df = pd.DataFrame(0, index=WLCR.index, columns=list(missing_LABEL))
            WLCR = pd.concat([WLCR, missing_df], axis=1)

        num_ones = (WLCR.values == 1).sum()
        print(f"\nFound {len(M[M['LCS'] > 0])} documents with non-empty Local Citations (LCS)\n")

    results = {
        'NetMatrix': WLCR,
        'histData': histData,
        'M': M,
        'LCS': M['LCS'].tolist()
    }

    return results


def lens(M, min_citations=0, sep=";", network=True):
    """
    Compute local citation scores for Lens.org exports.

    Lens CR fields contain Lens IDs (e.g. "002-554-834-643-65X") which map
    directly to the UT column of other documents in the collection.
    We match by resolved citation labels first, then fall back to Lens UT and DOI matching.
    """
    print("\nLens DB:\nSearching local citations (LCS) by Lens ID, DOI and resolved labels...\n")
    import re

    # Reset index name to prevent merge ambiguity
    if M.index.name == "SR":
        M.index.name = None

    M = M.sort_values(by="PY").reset_index(drop=True)
    M["Paper"] = np.arange(len(M))
    M["nLABEL"] = np.arange(len(M))

    # Clean UT (Lens ID) and DI (DOI) for matching
    M["UT_clean"] = M["UT"].fillna("").str.strip().str.upper()
    M["DI_clean"] = M["DI"].fillna("").str.strip().str.upper()

    # Reconstruct the resolved labels used during ETL to match converted reference strings
    resolved_labels = []
    for idx, row in M.iterrows():
        au_list = row["AU"] if isinstance(row["AU"], list) else []
        first_au = au_list[0] if au_list else "ANONYMOUS"
        py_raw = row["PY"]
        try:
            py = str(int(py_raw)) if pd.notna(py_raw) and py_raw else ""
        except (ValueError, TypeError):
            py = ""
        so = str(row["SO"]).strip().upper() if row["SO"] else ""
        parts = [p for p in [first_au, py, so] if p]
        label = ", ".join(parts).strip().upper()
        resolved_labels.append(label)

    M["resolved_label"] = resolved_labels

    # Build a flat table of (citing_paper, cited_ref) from CR column
    CR_rows = []
    for i, refs in enumerate(M["CR"]):
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if isinstance(ref, str) and ref.strip():
                CR_rows.append({"Paper": i, "ref": ref.strip().upper()})

    if not CR_rows:
        print("\nNo reference links found in Lens dataset.\n")
        M["LCS"] = 0
        histData = M[["SR_FULL", "TI", "DE", "ID", "DI", "PY", "LCS", "TC"]].copy()
        histData.columns = ["Paper", "Title", "Author_Keywords", "KeywordsPlus", "DOI", "Year", "LCS", "GCS"]
        histData = histData.sort_values(by="Year").reset_index(drop=True)
        return {"NetMatrix": None, "histData": histData, "M": M, "LCS": M["LCS"].tolist()}

    CR_df = pd.DataFrame(CR_rows)

    # Build mapping tables, ensuring unique keys to avoid InvalidIndexError
    ut_map = M[M["UT_clean"] != ""].drop_duplicates("UT_clean").set_index("UT_clean")["nLABEL"]
    doi_map = M[M["DI_clean"] != ""].drop_duplicates("DI_clean").set_index("DI_clean")["nLABEL"]
    label_map = M[M["resolved_label"] != ""].drop_duplicates("resolved_label").set_index("resolved_label")["nLABEL"]

    CR_df["matched_nLABEL_ut"] = CR_df["ref"].map(ut_map)
    CR_df["matched_nLABEL_doi"] = CR_df["ref"].map(doi_map)
    CR_df["matched_nLABEL_label"] = CR_df["ref"].map(label_map)

    # Combine: prefer resolved label match, fallback to UT, then DOI
    CR_df["cited_nLABEL"] = CR_df["matched_nLABEL_label"].combine_first(
        CR_df["matched_nLABEL_ut"]
    ).combine_first(
        CR_df["matched_nLABEL_doi"]
    )

    matched = CR_df.dropna(subset=["cited_nLABEL"]).copy()
    matched["cited_nLABEL"] = matched["cited_nLABEL"].astype(int)
    # Drop self-citations and deduplicate
    matched = matched[matched["Paper"] != matched["cited_nLABEL"]]
    matched = matched.drop_duplicates(subset=["Paper", "cited_nLABEL"])

    print(f"\nFound {len(matched)} internal citation links out of {len(CR_df)} total references\n")

    # Compute LCS
    LCS_counts = matched.groupby("cited_nLABEL").size().reset_index(name="LCS")
    M["LCS"] = M["nLABEL"].map(LCS_counts.set_index("cited_nLABEL")["LCS"]).fillna(0).astype(int)

    # Prepare histData
    histData = M[["SR_FULL", "TI", "DE", "ID", "DI", "PY", "LCS", "TC"]].copy()
    histData.columns = ["Paper", "Title", "Author_Keywords", "KeywordsPlus", "DOI", "Year", "LCS", "GCS"]
    histData = histData.sort_values(by="Year").reset_index(drop=True)

    WLCR = None
    if network:
        # Build self-citations to ensure every document exists in both index (citing) and columns (cited)
        all_sr = M["SR_FULL"].unique()
        self_citations = pd.DataFrame({"citing": all_sr, "cited": all_sr, "val": 1})

        if not matched.empty:
            citing_labels = M.loc[matched["Paper"], "SR_FULL"].values
            cited_labels  = M.loc[matched["cited_nLABEL"], "SR_FULL"].values
            net_df = pd.DataFrame({"citing": citing_labels, "cited": cited_labels, "val": 1})
            net_df = pd.concat([net_df, self_citations]).drop_duplicates(subset=["citing", "cited"])
        else:
            net_df = self_citations.copy()

        WLCR = net_df.pivot_table(index="citing", columns="cited", values="val", fill_value=0)
        # Ensure index and columns are exactly aligned and in the same order
        WLCR = WLCR.reindex(index=all_sr, columns=all_sr, fill_value=0)

        print(f"\nLCS network built: {len(M[M['LCS'] > 0])} documents with local citations\n")

    return {
        "NetMatrix": WLCR,
        "histData": histData,
        "M": M,
        "LCS": M["LCS"].tolist()
    }

def scopus(M, min_citations=0, sep=";", network=True):

    print("\nScopus DB:\nProcessing citations...\n")
    import re
    
    # Reset index name to prevent ambiguous merge errors if the index is named 'SR'
    if M.index.name == 'SR':
        M.index.name = None

    # Process the citations
    CR = M['CR']
    CR = pd.DataFrame({
        'SR_citing': np.repeat(M['SR'], CR.str.len()),
        'ref': [item for sublist in CR for item in sublist]
    })
    
    # Clean string helper matching R's clean strategy
    def clean_string(s):
        if not isinstance(s, str):
            return ""
        s = s.upper()
        s = re.sub(r'[^A-Z0-9\s]', ' ', s)
        return ' '.join(s.split())

    M['TI_clean'] = M['TI'].fillna("").apply(clean_string)
    CR['ref_clean'] = CR['ref'].fillna("").apply(clean_string)

    # Perform title-based substring matching
    matched_records = []
    for idx, row in M.iterrows():
        ti_clean = row['TI_clean']
        if not ti_clean or len(ti_clean) < 4:
            continue
        # Find matching references
        mask = CR['ref_clean'].str.contains(ti_clean, regex=False)
        matches = CR[mask]
        for _, match_row in matches.iterrows():
            matched_records.append({
                'SR_citing': match_row['SR_citing'],
                'SR_cited': row['SR']
            })

    CR_matched = pd.DataFrame(matched_records)
    print(f"\nFound {len(CR_matched)} matching citations...\n")
    
    # Calculate the Local Citation Score (LCS)
    if not CR_matched.empty:
        LCS = CR_matched.groupby('SR_cited').size().reset_index(name='LCS')
        # Merge LCS scores with M
        M = M.merge(LCS, left_on='SR', right_on='SR_cited', how='left').fillna({'LCS': 0})
    else:
        M = M.copy()
        M['LCS'] = 0.0
    
    print(f"\nCalculated Local Citation Scores (LCS) for {len(M)} papers...\n")
    
    # Select and rename columns for historical data
    histData = M[['SR_FULL', 'TI', 'DE', 'ID', 'DI', 'PY', 'LCS', 'TC']].copy()
    histData.columns = ['Paper', 'Title', 'Author_Keywords', 'KeywordsPlus', 'DOI', 'Year', 'LCS', 'GCS']
    histData = histData.sort_values(by='Year').reset_index(drop=True)
    
    # Build the co-citation matrix if network is True
    WLCR = None
    if network:
        print("\nBuilding co-citation matrix...\n")
        
        # Add self-citations to ensure each document cites itself
        CRadd = pd.DataFrame({'SR_citing': M['SR'].unique(), 'SR_cited': M['SR'].unique(), 'value': 1})
        
        if not CR_matched.empty:
            WLCR = CR_matched[['SR_citing', 'SR_cited']].copy()
            WLCR['value'] = 1
            WLCR = pd.concat([WLCR, CRadd]).drop_duplicates()
        else:
            WLCR = CRadd.copy()
        
        WLCR = WLCR.pivot_table(index='SR_citing', columns='SR_cited', values='value', fill_value=0)
        
        # Filter only the rows corresponding to cited documents
        WLCR = WLCR.loc[WLCR.index.isin(CRadd['SR_cited'])]
        print(f"\nCo-citation matrix built with {WLCR.shape[0]} rows and {WLCR.shape[1]} columns...\n")
    
    results = {
        'NetMatrix': WLCR,
        'histData': histData,
        'M': M,
        'LCS': M['LCS'].tolist()
    }

    return results

