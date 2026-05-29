from .utils import *
from .cocmatrix import *


def biblionetwork(M, analysis="coupling", network="authors", n=None, sep=";", short=False, shortlabel=True, remove_terms=None, synonyms=None):
    
    def crossprod(A, B):
        if A is None or B is None:
            return None
        return A.T @ B  # Moltiplicazione matriciale per ottenere il prodotto incrociato

    NetMatrix = None

    if analysis == "coupling":
        if network == "authors":
            WA = cocMatrix(M, Field="AU", type="sparse", n=n, sep=sep, short=short)
            WCR = cocMatrix(M, Field="CR", type="sparse", n=n, sep=sep, short=short)
            CRA = crossprod(WCR, WA)
            NetMatrix = crossprod(CRA, CRA)
        elif network == "references":
            WCR = cocMatrix(M, Field="CR", type="sparse", n=n, sep=sep, short=short)
            if WCR is not None:
                WCR = WCR.T
            NetMatrix = crossprod(WCR, WCR)
        elif network == "sources":
            WSO = cocMatrix(M, Field="SO", type="sparse", n=n, sep=sep, short=short)
            WCR = cocMatrix(M, Field="CR", type="sparse", n=n, sep=sep, short=short)
            CRSO = crossprod(WCR, WSO)
            NetMatrix = crossprod(CRSO, CRSO)
        elif network == "countries":
            WCO = cocMatrix(M, Field="AU_CO", type="sparse", n=n, sep=sep, short=short)
            WCR = cocMatrix(M, Field="CR", type="sparse", n=n, sep=sep, short=short)
            CRCO = crossprod(WCR, WCO)
            NetMatrix = crossprod(CRCO, CRCO)

    elif analysis == "co-occurrences":
        if network == "authors":
            WA = cocMatrix(M, Field="AU", type="sparse", n=n, sep=sep, short=short)
        elif network == "keywords":
            WA = cocMatrix(M, Field="ID", type="sparse", n=n, sep=sep, short=short, remove_terms=remove_terms, synonyms=synonyms)
        elif network == "author_keywords":
            WA = cocMatrix(M, Field="DE", type="sparse", n=n, sep=sep, short=short, remove_terms=remove_terms, synonyms=synonyms)
        elif network == "titles":
            WA = cocMatrix(M, Field="TI_TM", type="sparse", n=n, sep=sep, short=short, remove_terms=remove_terms, synonyms=synonyms)
        elif network == "abstracts":
            WA = cocMatrix(M, Field="AB_TM", type="sparse", n=n, sep=sep, short=short, remove_terms=remove_terms, synonyms=synonyms)
        elif network == "sources":
            WA = cocMatrix(M, Field="SO", type="sparse", n=n, sep=sep, short=short)
        NetMatrix = crossprod(WA, WA)

    elif analysis == "co-citation":
        if network == "authors":
            WA = cocMatrix(M, Field="CR_AU", type="sparse", n=n, sep=sep, short=short)
        elif network == "references":
            WA = cocMatrix(M, Field="CR", type="sparse", n=n, sep=sep, short=short)
        elif network == "sources":
            WA = cocMatrix(M, Field="CR_SO", type="sparse", n=n, sep=sep, short=short)
        NetMatrix = crossprod(WA, WA)

    elif analysis == "collaboration":
        if network == "authors":
            WA = cocMatrix(M, Field="AU", type="sparse", n=n, sep=sep, short=short)
        elif network == "universities":
            WA = cocMatrix(M, Field="AU_UN", type="sparse", n=n, sep=sep, short=short)
        elif network == "countries":
            WA = cocMatrix(M, Field="AU_CO", type="sparse", n=n, sep=sep, short=short)
        NetMatrix = crossprod(WA, WA)

    # Verifica che NetMatrix non sia None prima di procedere
    if NetMatrix is not None:
        NetMatrix = pd.DataFrame(NetMatrix)  # Converti in DataFrame se necessario

        # Eliminazione delle colonne e righe vuote
        filtered_columns = [col for col in NetMatrix.columns if str(col).strip()]
        filtered_index = [idx for idx in NetMatrix.index if str(idx).strip()]
        NetMatrix = NetMatrix.loc[filtered_index, filtered_columns]

        M = M.get()  # Estrai il dizionario se M è un oggetto

        db_name = M["DB"].iloc[0]
        print(f"db_name: {db_name}")
        if network == "references" and db_name == "SCOPUS":
            ind = [i for i, col in enumerate(NetMatrix.columns) if str(col)[0].isalpha()]
            NetMatrix = NetMatrix.iloc[ind, ind]

        if network == "references" and shortlabel:
            LABEL = label_short(NetMatrix, db=db_name.lower())
            LABEL = remove_duplicated_labels(LABEL)
            NetMatrix.columns = NetMatrix.index = LABEL

    return NetMatrix


def label_short(NET, db="isi"):
    LABEL = pd.Series(NET.columns)
    YEAR = LABEL.str.extract(r'(\d{4})')[0].fillna("")

    if db == "web_of_science":
        AU = LABEL.str.split(" ").str[:2].str.join(" ")
        LABEL = AU + " " + YEAR
    elif db == "scopus":
        AU = LABEL.str.split(". ").str[0]
        LABEL = AU + ". " + YEAR
    return LABEL.tolist()


def remove_duplicated_labels(LABEL):
    LABEL = pd.Series(LABEL)
    counts = LABEL.value_counts()
    duplicates = counts[counts > 1].index

    for dup in duplicates:
        dup_indices = LABEL[LABEL == dup].index
        LABEL.iloc[dup_indices] = [f"{dup}-{i+1}" for i in range(len(dup_indices))]

    return LABEL.tolist()
