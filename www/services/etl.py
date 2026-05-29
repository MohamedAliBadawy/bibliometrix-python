"""
ETL Pipeline for Bibliometrix-Python
=====================================

Implements a robust Extract → Transform → Validate → Load pipeline for 
source-agnostic bibliometric data processing. This module acts as the central
``convert2df()``-equivalent for the Python port of Bibliometrix.

Supported data sources:
    - Web of Science (TXT/CIW)
    - Scopus (CSV)
    - Dimensions (CSV/XLSX)
    - PubMed (TXT, XML)
    - Cochrane (TXT)
    - OpenAlex (API, via api_retriever)

Architecture
------------
The pipeline enforces the WoS internal schema used by downstream analytical
functions.  Column mappings are defined declaratively in ``SOURCE_MAPPINGS``,
avoiding hard-coded if/else branches for every source.

Multi-value fields (AU, AF, C1, CR, DE, ID) are stored as Python ``list[str]``
in the in-memory DataFrame.  When serialised to CSV the semicolon (``;``) is
used as the internal delimiter.

Null Handling
~~~~~~~~~~~~~
* Multi-value fields → ``[]``
* Scalar fields → ``""``
* ``TC`` (Times Cited) → ``0``
"""

import pandas as pd
import re
from typing import Dict, List, Any, Optional
from www.services.parsers import (
    parse_wos_data,
    parse_pubmed_data,
    parse_cochrane_data,
    parse_pubmed_xml,
)
from www.services.metatagextraction import SR

# ---------------------------------------------------------------------------
#  Target schema – the 24 mandatory WoS-style columns
# ---------------------------------------------------------------------------
TARGET_SCHEMA = [
    "DB", "UT", "DI", "PMID", "TI", "SO", "JI", "PY", "DT", "LA", "TC",
    "AU", "AF", "C1", "RP", "CR", "DE", "ID", "AB", "VL", "IS", "BP", "EP", "SR", "C3",
]

# Columns that must be lists of strings
LIST_FIELDS = ["AU", "AF", "C1", "CR", "DE", "ID"]

# ---------------------------------------------------------------------------
#  Source → WoS column mapping dictionaries
# ---------------------------------------------------------------------------
SOURCE_MAPPINGS: Dict[str, Dict[str, str]] = {
    "WEB_OF_SCIENCE": {
        # WoS parser already uses the correct tags; identity mapping.
        "UT": "UT", "DI": "DI", "TI": "TI", "SO": "SO", "JI": "JI",
        "PY": "PY", "DT": "DT", "LA": "LA", "TC": "TC",
        "AU": "AU", "AF": "AF", "C1": "C1", "RP": "RP", "CR": "CR",
        "DE": "DE", "ID": "ID", "AB": "AB", "VL": "VL", "IS": "IS",
        "BP": "BP", "EP": "EP", "C3": "C3",
    },
    "SCOPUS": {
        "EID": "UT",
        "DOI": "DI",
        "Title": "TI",
        "Source title": "SO",
        "Abbreviated Source Title": "JI",
        "Year": "PY",
        "Document Type": "DT",
        "Language of Original Document": "LA",
        "Cited by": "TC",
        "Authors": "AU",
        "Author full names": "AF",
        "Authors with affiliations": "C1",
        "Affiliations": "C1",          # fallback column name
        "Correspondence Address": "RP",
        "References": "CR",
        "Author Keywords": "DE",
        "Index Keywords": "ID",
        "Abstract": "AB",
        "Volume": "VL",
        "Issue": "IS",
        "Page start": "BP",
        "Page end": "EP",
        "PubMed ID": "PMID",
    },
    "PUBMED": {
        "PMID": "UT",
        "DOI": "DI",
        "LID": "DI",
        "TI": "TI",
        "JT": "SO",
        "TA": "JI",
        "DP": "PY",
        "PT": "DT",
        "LA": "LA",
        "Cited": "TC",
        "AU": "AU",
        "FAU": "AF",
        "AD": "C1",
        "CR": "CR",
        "OT": "DE",
        "MH": "ID",
        "AB": "AB",
        "VI": "VL",
        "IP": "IS",
        "PG": "BP",
    },
    "DIMENSIONS": {
        "Publication ID": "UT",
        "DOI": "DI",
        "Title": "TI",
        "Source title": "SO",
        "PubYear": "PY",
        "Publication Type": "DT",
        "Times cited": "TC",
        "Authors": "AU",
        "Authors Affiliations": "C1",
        "Authors (Raw Affiliation)": "C1",
        "Corresponding Authors": "RP",
        "References": "CR",
        "Author Keywords": "DE",
        "MeSH terms": "ID",
        "Abstract": "AB",
        "Volume": "VL",
        "Issue": "IS",
        "Pagination": "BP",
        "PMID": "PMID",
    },
    "OPENALEX": {
        # OpenAlex API fields – already pre-mapped by api_retriever
        "UT": "UT", "DI": "DI", "TI": "TI", "SO": "SO", "JI": "JI",
        "PY": "PY", "DT": "DT", "LA": "LA", "TC": "TC",
        "AU": "AU", "AF": "AF", "C1": "C1", "RP": "RP", "CR": "CR",
        "DE": "DE", "ID": "ID", "AB": "AB", "VL": "VL", "IS": "IS",
        "BP": "BP", "EP": "EP",
    },
    "LENS": {
        "Lens ID": "UT",
        "DOI": "DI",
        "Title": "TI",
        "Source Title": "SO",
        "Source Title Abbreviation": "JI",
        "Publication Year": "PY",
        "Document Type": "DT",
        "Languages": "LA",
        "Citing Works Count": "TC",
        "Authors": "AU",
        "Author/s": "AU",
        "Author Affiliations": "C1",
        "References": "CR",
        "Keywords": "DE",
        "Fields of Study": "ID",
        "Abstract": "AB",
        "Volume": "VL",
        "Issue": "IS",
        "Start Page": "BP",
        "End Page": "EP",
        "PMID": "PMID",
    },
    "COCHRANE": {
        "ID": "UT",
        "DOI": "DI",
        "TI": "TI",
        "SO": "SO",
        "YR": "PY",
        "PT": "DT",
        "KY": "DE",
        "AB": "AB",
        "VL": "VL",
        "NO": "IS",
        "PG": "BP",
        "PM": "PMID",
    },
}


# ===================================================================
#  Phase 1: EXTRACT
# ===================================================================

def extract(source: str, path: str) -> List[Dict[str, Any]]:
    """
    Extract raw bibliographic records from a file.

    Dispatches to the correct parser based on ``source``.  For Scopus CSV
    and Dimensions CSV/XLSX the standard pandas readers are used.  For
    text-based formats the existing Bibliometrix-Python parsers are invoked.

    Args:
        source: Identifier of the data source.  One of
            ``"WEB_OF_SCIENCE"``, ``"SCOPUS"``, ``"PUBMED"``,
            ``"DIMENSIONS"``, ``"COCHRANE"``.
        path: Filesystem path to the raw export file.

    Returns:
        A list of dictionaries, each representing one bibliographic record
        with the original/source-specific column names.

    Raises:
        ValueError: If ``source`` is not a recognised data source.
        FileNotFoundError: If ``path`` does not exist.
    """
    source_upper = source.upper()
    is_xml = path.lower().endswith(".xml")

    if source_upper == "WEB_OF_SCIENCE":
        raw = parse_wos_data(path)
        # WoS parser returns values wrapped in lists – flatten scalar fields
        return _flatten_wos_records(raw)

    elif source_upper == "PUBMED":
        if is_xml:
            return parse_pubmed_xml(path)
        else:
            return parse_pubmed_data(path)

    elif source_upper == "COCHRANE":
        return parse_cochrane_data(path)

    elif source_upper == "SCOPUS":
        df = pd.read_csv(path)
        return df.to_dict(orient="records")

    elif source_upper == "DIMENSIONS":
        if path.lower().endswith(".xlsx") or path.lower().endswith(".xls"):
            try:
                df_first = pd.read_excel(path, header=None, nrows=1)
                first_val = str(df_first.iloc[0, 0]) if not df_first.empty else ""
                if "about the" in first_val.lower() or "criteria" in first_val.lower() or "©" in first_val.lower() or df_first.shape[1] < 3:
                    df = pd.read_excel(path, skiprows=1)
                else:
                    df = pd.read_excel(path)
            except Exception:
                df = pd.read_excel(path)
        else:
            try:
                df_first = pd.read_csv(path, header=None, nrows=1)
                first_val = str(df_first.iloc[0, 0]) if not df_first.empty else ""
                if "about the" in first_val.lower() or "criteria" in first_val.lower() or "©" in first_val.lower() or df_first.shape[1] < 3:
                    df = pd.read_csv(path, skiprows=1)
                else:
                    df = pd.read_csv(path)
            except Exception:
                df = pd.read_csv(path)
        print(f"\n[ETL] Loaded DIMENSIONS file. Columns found: {df.columns.tolist()}\n")
        return df.to_dict(orient="records")

    elif source_upper == "LENS":
        df = pd.read_csv(path)
        print(f"\n[ETL] Loaded LENS file. Columns found: {df.columns.tolist()}\n")
        return df.to_dict(orient="records")

    else:
        raise ValueError(
            f"Unsupported source: {source}. "
            f"Supported: WEB_OF_SCIENCE, SCOPUS, PUBMED, DIMENSIONS, COCHRANE, LENS"
        )


def _flatten_wos_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Flatten WoS parser output where every value is a list.

    The WoS TXT/CIW parser stores every field as a Python list (even scalar
    fields like ``TI``).  Multi-value fields (AU, AF, C1, CR, DE, ID) are
    kept as lists; all others are joined into a single string.

    Args:
        records: Raw records from ``parse_wos_data()``.

    Returns:
        Records with scalar fields collapsed to strings.
    """
    wos_list_keys = {"AU", "AF", "C1", "CR", "DE", "ID"}
    flat = []
    for rec in records:
        new_rec = {}
        for k, v in rec.items():
            if isinstance(v, list):
                if k in wos_list_keys:
                    # Keep as list — these are multi-value fields
                    new_rec[k] = v
                else:
                    # Join into a single string for scalar fields
                    new_rec[k] = " ".join(v).strip()
            else:
                new_rec[k] = v
        flat.append(new_rec)
    return flat


# ===================================================================
#  Phase 2: TRANSFORM (Rename + Type enforcement)
# ===================================================================

def transform(raw_data: List[Dict[str, Any]], source: str) -> pd.DataFrame:
    """
    Transform raw records into the standardised WoS-style DataFrame.

    Steps performed:
      1. Build DataFrame from the list of dicts.
      2. Rename columns using the declarative ``SOURCE_MAPPINGS`` dictionary.
      3. Ensure every column in ``TARGET_SCHEMA`` exists.
      4. Set the ``DB`` provenance column.
      5. Cast multi-value fields to ``list[str]``.
      6. Cast ``TC`` to ``int``, ``PY`` to ``str``.
      7. Replace all remaining ``NaN``/``None`` with ``""`` or ``[]``.

    Args:
        raw_data: Output of :func:`extract` — a list of dicts with
            source-specific column names.
        source: Identifier of the data source (e.g. ``"SCOPUS"``).

    Returns:
        A pandas DataFrame conforming to ``TARGET_SCHEMA``.
    """
    df = pd.DataFrame(raw_data)
    source_upper = source.upper()
    mapping = SOURCE_MAPPINGS.get(source_upper, {}).copy()

    # Dynamic column mapping for Dimensions keywords/concepts fallback
    if source_upper == "DIMENSIONS":
        keyword_col = None
        concept_col = None
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if "keyword" in col_lower:
                keyword_col = col
                break
            elif "concept" in col_lower:
                concept_col = col
        if keyword_col:
            mapping[keyword_col] = "DE"
        elif concept_col:
            mapping[concept_col] = "DE"

    # Build rename_map: source_col -> target_col
    # Only include source columns that actually exist in the data
    rename_map = {}
    target_names_used = set()
    for src_col, tgt_col in mapping.items():
        if src_col in df.columns and tgt_col not in target_names_used:
            rename_map[src_col] = tgt_col
            target_names_used.add(tgt_col)

    # Drop raw columns that would collide with renamed targets
    # e.g., PubMed raw data has "IS" (ISSN), but "IP" → "IS" (issue) rename
    #        would create duplicate "IS" columns
    cols_being_renamed = set(rename_map.keys())
    target_names = set(rename_map.values())
    for col in list(df.columns):
        if col not in cols_being_renamed and col in target_names:
            df = df.drop(columns=[col])

    df = df.rename(columns=rename_map)

    # Ensure all target columns exist
    for col in TARGET_SCHEMA:
        if col not in df.columns:
            if col in LIST_FIELDS:
                df[col] = [[] for _ in range(len(df))]
            else:
                df[col] = ""

    # Set DB column
    df["DB"] = source_upper

    # --- Source-specific post-processing ---

    # PubMed: extract 4-digit year from DP field
    if source_upper == "PUBMED":
        df["PY"] = df["PY"].astype(str).apply(_extract_year)
        # Set PMID from UT if not already set
        if df["PMID"].eq("").all():
            df["PMID"] = df["UT"]

    # Dimensions: handle Pagination → BP/EP
    if source_upper == "DIMENSIONS":
        if "Pagination" in df.columns:
            _split_pagination(df)

    # Scopus: ensure string conversion for Page columns
    if source_upper == "SCOPUS":
        for col in ["BP", "EP"]:
            df[col] = df[col].apply(
                lambda x: str(x).strip() if pd.notna(x) and str(x).strip() not in ("", "nan") else ""
            )

    # Cochrane: split PG into BP and EP, clean PMID values
    if source_upper == "COCHRANE":
        def _split_cochrane_pages(val):
            if not val:
                return "", ""
            s = str(val).strip()
            parts = re.split(r"[-‐–—]", s, maxsplit=1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
            return s, ""

        if "BP" in df.columns:
            splits = df["BP"].apply(_split_cochrane_pages)
            df["BP"] = splits.apply(lambda x: x[0])
            df["EP"] = splits.apply(lambda x: x[1])

        if "PMID" in df.columns:
            df["PMID"] = df["PMID"].astype(str).str.replace(r"(?i)\bPUBMED\b", "", regex=True).str.strip()

    # --- Multi-value fields to lists ---
    for field in LIST_FIELDS:
        df[field] = df[field].apply(lambda val, f=field: _to_list(val, f))

    # --- Lens: normalize AU full names → LASTNAME I (R-compatible format) ---
    # --- Lens: resolve CR Lens IDs → readable citation strings ---
    if source_upper == "LENS":
        def _lens_name_to_biblio(name: str) -> str:
            """Convert 'First Middle Last' → 'LAST F' (R bibliometrix format)."""
            name = name.strip()
            if not name:
                return name
            # Already in LASTNAME, F format — leave alone
            if "," in name:
                return name.upper()
            parts = name.split()
            if len(parts) == 1:
                return parts[0].upper()
            last = parts[-1].upper()
            initials = "".join(p[0].upper() for p in parts[:-1])
            return f"{last} {initials}"

        df["AU"] = df["AU"].apply(
            lambda authors: [_lens_name_to_biblio(a) for a in authors] if isinstance(authors, list) else authors
        )

        # Build UT → citation string lookup so CR Lens IDs become readable
        # Format: "LASTNAME F, YEAR, SOURCE TITLE"
        def _make_lens_cr_label(row):
            au_list = row["AU"] if isinstance(row["AU"], list) else []
            first_au = au_list[0] if au_list else "ANONYMOUS"
            py_raw = row["PY"]
            try:
                py = str(int(py_raw)) if pd.notna(py_raw) and py_raw else ""
            except (ValueError, TypeError):
                py = ""
            so = str(row["SO"]).strip().upper() if row["SO"] else ""
            parts = [p for p in [first_au, py, so] if p]
            return ", ".join(parts)

        ut_to_label = {}
        for _, row in df.iterrows():
            ut_val = str(row["UT"]).strip().upper()
            if ut_val and ut_val not in ("", "NAN"):
                ut_to_label[ut_val] = _make_lens_cr_label(row)

        def _resolve_lens_cr(refs):
            if not isinstance(refs, list):
                return refs
            resolved = []
            for ref in refs:
                ref_upper = str(ref).strip().upper()
                # If it looks like a Lens ID (alphanumeric + hyphens, no spaces, len ~18)
                # try to resolve it; otherwise keep as-is
                if ref_upper in ut_to_label:
                    resolved.append(ut_to_label[ref_upper])
                else:
                    resolved.append(ref)  # external reference — keep raw
            return resolved

        df["CR"] = df["CR"].apply(_resolve_lens_cr)

    # --- Keyword Fallback Logic (R-compatible) ---
    # In R's bibliometrix, if one keyword field (DE/Author Keywords or ID/Keywords Plus)
    # is completely empty but the other is populated, the populated one is copied to the other.
    # This is especially crucial for Dimensions files where MeSH terms map to ID, leaving DE empty.
    has_de = df["DE"].apply(lambda x: len(x) > 0).any()
    has_id = df["ID"].apply(lambda x: len(x) > 0).any()
    if not has_de and has_id:
        df["DE"] = df["ID"].copy()
    elif has_de and not has_id:
        df["ID"] = df["DE"].copy()

    # --- Numeric casting ---
    df["TC"] = pd.to_numeric(df["TC"], errors="coerce").fillna(0).astype(int)

    # --- Year as int (downstream functions do arithmetic on PY) ---
    # Prioritise Early Access (EA) year if present to match R's early access preference standard
    if "EA" in df.columns:
        # Convert EA to string
        df["EA_str"] = df["EA"].apply(lambda x: " ".join(x) if isinstance(x, list) else str(x))
        df["EA_year"] = df["EA_str"].astype(str).apply(_extract_year)
        df["EA_year"] = pd.to_numeric(df["EA_year"], errors="coerce").fillna(0).astype(int)
        
        df["PY"] = df["PY"].astype(str).apply(_extract_year)
        df["PY"] = pd.to_numeric(df["PY"], errors="coerce").fillna(0).astype(int)
        
        mask = df["EA_year"] > 1900
        df.loc[mask, "PY"] = df.loc[mask, "EA_year"]
        
        # Cleanup temp columns
        df = df.drop(columns=["EA_str", "EA_year"])
    else:
        df["PY"] = df["PY"].astype(str).apply(_extract_year)
        df["PY"] = pd.to_numeric(df["PY"], errors="coerce").fillna(0).astype(int)

    # --- Final NaN cleanup ---
    int_cols = {"TC", "PY"}
    for col in df.columns:
        if col in LIST_FIELDS:
            df[col] = df[col].apply(lambda x: x if isinstance(x, list) else [])
        elif col in int_cols:
            # Numeric columns – ensure no NaN, keep as int
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = df[col].fillna("").astype(str).replace("nan", "")

    return df[TARGET_SCHEMA]


def _to_list(value, field_name: str = "") -> List[str]:
    """
    Convert a value to a list of strings.

    Handles semicolon/comma-delimited strings, NaN/None, and other types.

    Args:
        value: The value to convert.
        field_name: Optional name of the field (e.g. "DE", "ID") to allow comma-splitting.

    Returns:
        A list of stripped, non-empty strings.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    
    # Determine the correct separator: keywords and terms may use commas if no semicolon is present
    split_char = ";"
    
    if isinstance(value, list):
        items = []
        for x in value:
            s_val = str(x).strip()
            if s_val and s_val not in ("", "nan", "None"):
                cur_sep = ";"
                if field_name in ("DE", "ID") and ";" not in s_val and "," in s_val:
                    cur_sep = ","
                items.extend([item.strip() for item in s_val.split(cur_sep) if item.strip()])
        return items
    
    s = str(value)
    if s in ("", "nan", "None"):
        return []
    
    if field_name in ("DE", "ID") and ";" not in s and "," in s:
        split_char = ","
        
    return [item.strip() for item in s.split(split_char) if item.strip()]


def _extract_year(value) -> str:
    """
    Extract a 4-digit year from a value.

    Args:
        value: A string that may contain a date or year.

    Returns:
        A 4-digit year string, or ``""`` if no year found.
    """
    s = str(value)
    match = re.search(r"\d{4}", s)
    return match.group(0) if match else ""


def _split_pagination(df: pd.DataFrame) -> None:
    """
    Split a Dimensions 'Pagination' column (e.g. ``"123-456"``) into BP and EP.

    Modifies ``df`` in-place.

    Args:
        df: DataFrame that may contain a ``Pagination`` column.
    """
    def _split(val):
        s = str(val)
        if "-" in s:
            parts = s.split("-", 1)
            return parts[0].strip(), parts[1].strip()
        return s.strip(), ""

    if "Pagination" in df.columns:
        splits = df["Pagination"].apply(_split)
        # Only overwrite if BP/EP are empty
        if df["BP"].eq("").all() or (df["BP"].astype(str) == "nan").all():
            df["BP"] = splits.apply(lambda x: x[0])
        if df["EP"].eq("").all() or (df["EP"].astype(str) == "nan").all():
            df["EP"] = splits.apply(lambda x: x[1])


# ===================================================================
#  Phase 3: CALCULATED FIELDS
# ===================================================================

def add_sr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the Short Reference (SR) field using the existing Bibliometrix
    ``SR()`` function from ``metatagextraction.py``.

    The SR format is: ``"FirstAuthor_Surname, Publication_Year, Journal_Abbrev"``

    This is a critical primary key used in citation network analyses.

    Args:
        df: A standardised DataFrame with at least ``AU``, ``PY``, ``JI``,
            ``SO``, and ``DB`` columns.

    Returns:
        The same DataFrame with ``SR`` and ``SR_FULL`` columns populated.
    """
    try:
        df_with_sr = SR(df)
        return df_with_sr
    except Exception as e:
        # Fallback: generate SR manually if the existing function fails
        print(f"Warning: SR() function failed ({e}), generating SR manually.")
        first_authors = df["AU"].apply(
            lambda l: l[0] if isinstance(l, list) and len(l) > 0 else "NA"
        )
        journal = df["JI"].apply(
            lambda x: x if isinstance(x, str) and x.strip() else ""
        )
        # Use SO as fallback where JI is empty
        so_vals = df["SO"]
        journal = journal.mask(journal == "", so_vals)
        journal = journal.str.replace(".", " ", regex=False).str.strip()
        sr = first_authors + ", " + df["PY"].astype(str) + ", " + journal
        df["SR"] = sr.str.replace(r"\s+", " ", regex=True)
        df["SR_FULL"] = df["SR"]
        return df


# ===================================================================
#  Phase 4: VALIDATION
# ===================================================================

def validate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate the standardised DataFrame against the target schema.

    Checks performed:
      1. All mandatory columns from ``TARGET_SCHEMA`` are present.
      2. No ``NaN`` or ``None`` values remain.
      3. Multi-value columns contain Python lists (not raw strings).
      4. ``TC`` is an integer column.

    Args:
        df: The transformed DataFrame to validate.

    Returns:
        The validated DataFrame (unchanged if all checks pass).

    Raises:
        ValueError: If any validation check fails, with a descriptive
            message indicating the exact problem.
    """
    # 1. Check mandatory columns
    missing_cols = set(TARGET_SCHEMA) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing mandatory columns: {missing_cols}")

    # 2. Check no NaN/None
    if df.isnull().any().any():
        nan_cols = df.columns[df.isnull().any()].tolist()
        raise ValueError(
            f"DataFrame contains NaN or None values in columns: {nan_cols}"
        )

    # 3. Check list fields are lists
    for field in LIST_FIELDS:
        non_lists = df[field].apply(lambda x: not isinstance(x, list))
        if non_lists.any():
            raise ValueError(
                f"Field '{field}' must contain lists, but "
                f"{non_lists.sum()} rows contain non-list values"
            )

    # 4. Check TC is integer
    if not pd.api.types.is_integer_dtype(df["TC"]):
        raise ValueError(
            f"TC must be integer, got {df['TC'].dtype}"
        )

    return df


# ===================================================================
#  Phase 5: LOAD
# ===================================================================

def load(df: pd.DataFrame, output_path: Optional[str] = None) -> pd.DataFrame:
    """
    Export the validated DataFrame, optionally saving to CSV.

    When saving to CSV, multi-value list fields are serialised as
    semicolon-delimited strings for flat-file compatibility.

    Args:
        df: The validated, standardised DataFrame.
        output_path: Optional filesystem path for CSV export.
            If ``None``, no file is written.

    Returns:
        The DataFrame (unmodified in memory; only the CSV copy is flattened).
    """
    if output_path:
        df_csv = df.copy()
        for field in LIST_FIELDS:
            df_csv[field] = df_csv[field].apply(
                lambda x: ";".join(x) if isinstance(x, list) else str(x)
            )
        df_csv.to_csv(output_path, index=False)

    return df


# ===================================================================
#  MAIN PIPELINE ENTRY POINT
# ===================================================================

def etl_pipeline(
    source: str,
    path: str,
    output_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Execute the complete ETL pipeline: Extract → Transform → Validate → Load.

    This is the primary entry-point for file-based imports, equivalent to
    ``convert2df()`` in the R version of Bibliometrix.

    Args:
        source: Data source identifier.  One of ``"WEB_OF_SCIENCE"``,
            ``"SCOPUS"``, ``"PUBMED"``, ``"DIMENSIONS"``, ``"COCHRANE"``.
        path: Path to the raw export file.
        output_path: Optional path to save the standardised CSV.

    Returns:
        A validated, standardised pandas DataFrame ready for downstream
        analytical functions.

    Raises:
        ValueError: On extraction errors, validation failures, or
            unsupported sources.

    Example::

        df = etl_pipeline("SCOPUS", "sources/Scopus/Scopus.csv",
                          output_path="standardized.csv")
    """
    raw_data = extract(source, path)
    df = transform(raw_data, source)
    df = validate(df)
    df = add_sr(df)
    df = load(df, output_path)
    return df