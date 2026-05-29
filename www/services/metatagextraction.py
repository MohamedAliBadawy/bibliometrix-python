from .utils import *


def metaTagExtraction(df, Field="AU_CO", sep=";", aff_disamb=False):
    """
    Extract metadata tags from a DataFrame based on the specified field.
    
    Args:
        df: A DataFrame object containing the data.
        Field: The field to extract metadata tags from.
        sep: The separator used to split the metadata tags.
        aff_disamb: A boolean value indicating whether to disambiguate the affiliations.
    
    Returns:
        A DataFrame with the extracted metadata tags.
    """
    M = df.get()

    if Field == "SR":
        M = SR(M)

    if Field == "CR_AU":
        M = CR_AU(M)

    if Field == "CR_SO":
        M = CR_SO(M)

    if Field == "AU_CO":
        M = AU_CO(M)

    if Field == "AU1_CO":
        M = AU1_CO(M)

    if Field == "AU_UN":
        if aff_disamb:
            M = AU_UN(M, sep)
        else:
            C1_str = M["C1"].apply(lambda x: sep.join(x) if isinstance(x, list) else str(x) if pd.notna(x) else "")
            M["AU_UN"] = C1_str.str.replace(r"\[.*?\] ", "", regex=True)
            M["AU1_UN"] = M["RP"].str.split(sep).apply(lambda l: l[0] if isinstance(l, list) else l)
            ind = M["AU1_UN"].str.find("),")
            a = ind[ind > -1].index
            M.loc[a, "AU1_UN"] = M.loc[a, "AU1_UN"].str[ind[a] + 2:]

    df.set(M)
    
    return df


def SR(M):
    listAU = M["AU"].apply(lambda l: [x.strip() for x in l])
    if M["DB"].iloc[0].lower() == "scopus":
        listAU = listAU.apply(lambda l: [x.replace(" ", ",").replace(",,", ",").replace(" ", "") for x in l])
    FirstAuthors = listAU.apply(lambda l: l[0] if len(l) > 0 else "NA").str.replace(",", " ")

    no_art = M["JI"] == ""
    M.loc[no_art, "JI"] = M.loc[no_art, "SO"]
    J9 = M["JI"].str.replace(".", " ", regex=False).str.strip()
    SR = FirstAuthors + ", " + M["PY"].astype(str) + ", " + J9

    M["SR_FULL"] = SR.str.replace(r"\s+", " ", regex=True)

    st = i = 0
    while st == 0:
        ind = SR.duplicated()
        if ind.any():
            i += 1
            SR[ind] = SR[ind] + "-" + chr(96 + i)
        else:
            st = 1
    M["SR"] = SR.str.replace(r"\s+", " ", regex=True)
    
    return M


# TO BE DONE
def CR_AU(M):
    listCAU = M["CR"].apply(lambda x: x if isinstance(x, list) else []).apply(lambda l: [x for x in l if len(x) > 10])
    FCAU = listCAU.apply(lambda l: [x.split(",")[0].strip() for x in l])
    M["CR_AU"] = FCAU.apply(lambda l: ";".join(l))
    
    return M


def CR_SO(M):
    import re
    listCAU = M["CR"].apply(lambda x: x if isinstance(x, list) else [])
    if M["DB"].iloc[0].upper() != "SCOPUS":
        FCAU = listCAU.apply(lambda l: [x.split(",")[2].strip() for x in l if len(x.split(",")) > 2])
    else:
        def extract_scopus_journal(ref):
            if not isinstance(ref, str) or ref.strip() == "":
                return ""
            parts = [p.strip() for p in ref.split(',')]
            if len(parts) < 2:
                return ref
            # Remove year at the end if present
            if parts[-1].startswith('(') and parts[-1].endswith(')'):
                parts = parts[:-1]
            # Traverse from right to left to find the first non-numeric/non-short element
            for part in reversed(parts):
                if not part:
                    continue
                if part.lower().startswith('pp.') or part.lower().startswith('p.') or part.lower().startswith('art. no.'):
                    continue
                if re.match(r'^\d+$', part) or re.match(r'^\d+-\d+$', part):
                    continue
                if len(part) < 15 and re.match(r'^\d+\s+[A-Za-z]+', part):
                    continue
                if len(part) < 8 and (part.lower().startswith('vol.') or part.lower().startswith('no.')):
                    continue
                return part
            return parts[-1]

        FCAU = listCAU.apply(lambda l: [extract_scopus_journal(x) for x in l if len(x.split(",")) > 2])        
    
    M["CR_SO"] = FCAU.apply(lambda l: ";".join(l) if l else None) # da checkare
    
    return M


def AU_CO(M, log=False):
    # Read the list of countries
    with open("www/static/countries.txt", "r") as file:
        countries = file.read().splitlines()

    # Extract the countries from the affiliations
    M["AU_CO"] = None
    C1 = M["C1"]
    
    # Convert empty lists in C1 using the values from RP
    C1 = M["C1"].fillna(M["RP"])
    
    for i in range(len(C1)):
        # Check if the element is an empty list
        if isinstance(C1.iloc[i], list) and not C1.iloc[i]:
            if pd.notna(M["RP"].iloc[i]):  # Check if "RP" is valid
                C1.at[i] = [M["RP"].iloc[i]]  # Use at to assign directly
            else:  # If "RP" is also empty, assign an empty list
                C1.at[i] = []

    # Extract the countries from the affiliations
    results = []
    for i in range(len(M)):
        countries_found = []
        for c1 in C1.iloc[i]:
            if pd.notna(c1):
                clean_last = c1.split(",")[-1].strip().upper().replace("TURKIYE", "TURKEY").replace("TÜRKIYE", "TURKEY").replace("TÜRKİYE", "TURKEY")
                ind = [c.upper() for c in countries if re.search(r'\b' + re.escape(c.upper()) + r'\b', clean_last)]
                countries_found.extend(ind)
        results.append(countries_found)

    # Assign results to the AU_CO column
    M["AU_CO"] = results
    
    # Replace country names with standardized names
    M["AU_CO"] = M["AU_CO"].apply(lambda countries: [country.replace("UNITED STATES", "USA")
                                                     .replace("RUSSIAN FEDERATION", "RUSSIA")
                                                     .replace("TAIWAN", "CHINA")
                                                     .replace("ENGLAND", "UNITED KINGDOM")
                                                     .replace("SCOTLAND", "UNITED KINGDOM")
                                                     .replace("WALES", "UNITED KINGDOM")
                                                     .replace("NORTH IRELAND", "UNITED KINGDOM")
                                                     for country in countries])
    
    if log:
        with open("affiliations.txt", "w", encoding="utf-8") as file:
            for affiliation in M["AU_CO"]:
                file.write(f"{affiliation}\n")

    return M


def AU1_CO(M, log=False):
    # Read the list of countries
    with open("www/static/countries.txt", "r") as file:
        countries = [c.strip().upper() for c in file.read().splitlines() if c.strip()]

    size = len(M)
    results = [None] * size

    C1 = M["C1"].copy()
    RP = M["RP"].copy()

    # Match R's C1/RP override: C1[which(!is.na(M$RP))] <- M$RP[which(!is.na(M$RP))]
    for idx in range(size):
        rp_val = RP.iloc[idx]
        if pd.notna(rp_val) and str(rp_val).strip() != "" and str(rp_val).upper() != "NA":
            C1.iloc[idx] = rp_val

    import re

    # Process per-row to replicate R's regex parsing and fallback search
    for i in range(size):
        c1_val = C1.iloc[i]
        rp_val = RP.iloc[i]
        
        country_found = None
        
        # 1. Search in C1_processed
        if isinstance(c1_val, list):
            c1_val = ";".join([str(x) for x in c1_val])
            
        if pd.notna(c1_val) and str(c1_val).strip() != "" and str(c1_val).upper() != "NA":
            c1_str = str(c1_val)
            # gsub("\\[.*?\\] ", "", C1)
            c1_str = re.sub(r'\[.*?\]\s*', '', c1_str)
            # gsub("^.*?\\(REPRINT\\sAUTHOR\\)", "", C1)
            c1_str = re.sub(r'^.*\(REPRINT\s+AUTHOR\)', '', c1_str, flags=re.IGNORECASE)
            # unlist(lapply(strsplit(C1, sep), function(l) l[1]))
            parts = c1_str.split(";")
            first_part = parts[0] if parts else ""
            # gsub("^(.+)?,", "", C1) (removes everything before the last comma)
            if "," in first_part:
                last_comma_idx = first_part.rfind(",")
                processed_str = first_part[last_comma_idx + 1:]
            else:
                processed_str = first_part
            # gsub("[[:punct:][:blank:]]+", " ", C1)
            processed_str = re.sub(r'[^\w\s]', ' ', processed_str)  # replace punctuation
            processed_str = re.sub(r'\s+', ' ', processed_str)  # collapse whitespace
            processed_str = " " + processed_str.strip().upper() + " "
            
            for country in countries:
                spaced_country = " " + country + " "
                if spaced_country in processed_str:
                    country_found = country
                    break
                    
        # 2. Fallback: if M$AU1_CO[i] is NA, search the entire RP string
        if country_found is None and pd.notna(rp_val) and str(rp_val).strip() != "" and str(rp_val).upper() != "NA":
            rp_str = str(rp_val) + ";"
            rp_str = re.sub(r'[^\w\s]', ' ', rp_str)
            rp_str = re.sub(r'\s+', ' ', rp_str)
            rp_str = " " + rp_str.strip().upper() + " "
            
            for country in countries:
                spaced_country = " " + country + " "
                if spaced_country in rp_str:
                    country_found = country
                    break
                    
        if country_found:
            # Map countries using R's standardization rules
            country_found = country_found.replace("UNITED STATES", "USA")
            country_found = country_found.replace("RUSSIAN FEDERATION", "RUSSIA")
            country_found = country_found.replace("TAIWAN", "CHINA")
            country_found = country_found.replace("ENGLAND", "UNITED KINGDOM")
            country_found = country_found.replace("SCOTLAND", "UNITED KINGDOM")
            country_found = country_found.replace("WALES", "UNITED KINGDOM")
            country_found = country_found.replace("NORTH IRELAND", "UNITED KINGDOM")
            country_found = country_found.replace("TURKIYE", "TURKEY")
            country_found = country_found.replace("TÜRKIYE", "TURKEY")
            country_found = country_found.replace("TÜRKİYE", "TURKEY")
            country_found = country_found.replace("ESWATINI", "SWAZILAND")
            country_found = country_found.replace("CZECHIA", "CZECH REPUBLIC")
            
        results[i] = country_found
        
    M["AU1_CO"] = results

    if log:
        with open("first_author_countries.txt", "w", encoding="utf-8") as file:
            for affiliation in M["AU1_CO"]:
                file.write(f"{affiliation}\n")

    return M


# TO BE DONE
def AU_UN(M, sep):
    C1 = M["C1"].fillna(M["RP"])
    C1_str = C1.apply(lambda x: sep.join(x) if isinstance(x, list) else str(x) if pd.notna(x) else "")
    AFF = C1_str.str.replace(r"\[.*?\]\s*", "", regex=True)
    indna = AFF.isna() | (AFF == "")
    AFF[indna] = M["RP"][indna]
    AFF = AFF.str.strip()
    listAFF = AFF.str.split(sep)

    uTags = ["UNIV", "COLL", "SCH", "INST", "ACAD", "ECOLE", "CTR", "SCI", "CENTRE", "CENTER", "CENTRO", "HOSP", "ASSOC", "COUNCIL",
             "FONDAZ", "FOUNDAT", "ISTIT", "LAB", "TECH", "RES", "CNR", "ARCH", "SCUOLA", "PATENT OFF", "CENT LIB", "HEALTH", "NATL",
             "LIBRAR", "CLIN", "FDN", "OECD", "FAC", "WORLD BANK", "POLITECN", "INT MONETARY FUND", "CLIMA", "METEOR", "OFFICE", "ENVIR",
             "CONSORTIUM", "OBSERVAT", "AGRI", "MIT ", "INFN", "SUNY "]

    def extract_affiliations(l):
        index = []
        for item in l:
            item = item.replace("(REPRINT AUTHOR)", "")
            affL = item.split(",")
            indd = [i for i, aff in enumerate(affL) if any(tag in aff.upper() for tag in uTags)]
            if not indd:
                index.append("NOTREPORTED")
            elif any(char.isdigit() for char in affL[indd[0]]):
                index.append("NOTDECLARED")
            else:
                index.append(affL[indd[0]].strip().upper())
        return ";".join(index)

    M["AU_UN"] = listAFF.apply(extract_affiliations)
    if str(M["DB"].iloc[0]).upper() in ["ISI", "WEB_OF_SCIENCE", "OPENALEX"] and "C3" in M.columns:
        M.loc[M["C3"].notna() & (M["C3"] != ""), "AU_UN"] = M["C3"]
        M["AU_UN"] = M["AU_UN"].str.split(sep).apply(lambda l: sep.join([x.strip() for x in l]))

    M["AU_UN"] = M["AU_UN"].str.replace(r"\\&", "AND", regex=True).str.replace("&", "AND", regex=False)

    RP = M["RP"].fillna(M["C1"])
    RP_str = RP.apply(lambda x: sep.join(x) if isinstance(x, list) else str(x) if pd.notna(x) else "")
    AFF = RP_str.str.replace(r"\[.*?\]\s*", "", regex=True)
    indna = AFF.isna() | (AFF == "")
    AFF[indna] = RP_str[indna]
    AFF = AFF.str.strip()
    listAFF = AFF.str.split(sep)

    M["AU1_UN"] = listAFF.apply(extract_affiliations)
    M["AU1_UN"] = M["AU1_UN"].str.replace(r"\\&", "AND", regex=True).str.replace("&", "AND", regex=False)

    M["AU_UN_NR"] = None
    listAFF2 = M["AU_UN"].str.split(sep)
    cont = listAFF2.apply(lambda l: [i for i, x in enumerate(l) if x == "NR"])

    for i, indices in enumerate(cont):
        if indices:
            M.at[i, "AU_UN_NR"] = ";".join([listAFF.iloc[i][j] for j in indices])

    M["AU_UN"] = M["AU_UN"].replace({"NOTDECLARED": None, "NOTREPORTED": None})
    M["AU_UN"] = M["AU_UN"].str.replace("NOTREPORTED;", "", regex=False).str.replace(";NOTREPORTED", "", regex=False)
    M["AU_UN"] = M["AU_UN"].str.replace("NOTDECLARED;", "", regex=False).str.replace("NOTDECLARED", "", regex=False)
    
    return M
