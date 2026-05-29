"""
API Retriever for Advanced Level ETL
=====================================

Fetches bibliographic data from PubMed and OpenAlex REST APIs with:
  - **Pagination**: Handles multi-page result sets transparently.
  - **Rate limiting**: Token-bucket algorithm to respect API quotas.
  - **Retry with backoff**: Exponential backoff on transient failures.

The retrieved records are normalised into the same WoS-style schema used
by the file-based ETL pipeline, reusing ``transform()``, ``validate()``,
``add_sr()``, and ``load()`` from ``etl.py`` — no duplicated logic.

Usage::

    from www.services.api_retriever import api_etl_pipeline

    df = api_etl_pipeline("OPENALEX", "machine learning", max_results=200)
"""

import requests
import time
import xml.etree.ElementTree as ET
import pandas as pd
from typing import List, Dict, Any, Optional, Callable
from functools import wraps
from www.services.etl import transform, validate, add_sr, load

# ---------------------------------------------------------------------------
#  API Endpoints
# ---------------------------------------------------------------------------
PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
OPENALEX_BASE_URL = "https://api.openalex.org/"

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------
RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 1,
    "max_delay": 60,
    "backoff_factor": 2,
}

RATE_LIMIT_CONFIG = {
    "pubmed": {"requests_per_second": 3, "burst_size": 10},
    "openalex": {"requests_per_second": 10, "burst_size": 50},
}


# ===================================================================
#  Rate Limiter
# ===================================================================

class RateLimiter:
    """Token-bucket rate limiter for API requests.

    Attributes:
        requests_per_second: Rate at which tokens are replenished.
        burst_size: Maximum number of tokens available for burst requests.
    """

    def __init__(self, requests_per_second: float = 1, burst_size: int = 5):
        """
        Initialise the rate limiter.

        Args:
            requests_per_second: Sustained request rate.
            burst_size: Maximum tokens (for short bursts).
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()

    def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, blocking if necessary.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            Time waited in seconds.
        """
        start_time = time.time()
        while True:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.burst_size,
                self.tokens + elapsed * self.requests_per_second,
            )
            self.last_update = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return time.time() - start_time
            wait_time = (tokens - self.tokens) / self.requests_per_second
            time.sleep(min(wait_time, 0.1))


# ===================================================================
#  Retry Decorator
# ===================================================================

def retry_with_backoff(
    max_retries: int = RETRY_CONFIG["max_retries"],
    initial_delay: float = RETRY_CONFIG["initial_delay"],
    max_delay: float = RETRY_CONFIG["max_delay"],
    backoff_factor: float = RETRY_CONFIG["backoff_factor"],
    exceptions: tuple = (requests.RequestException,),
):
    """
    Decorator for retrying failed HTTP requests with exponential backoff.

    Args:
        max_retries: Maximum retry attempts.
        initial_delay: Initial delay in seconds before first retry.
        max_delay: Upper bound for delay between retries.
        backoff_factor: Multiplier applied to delay after each failure.
        exceptions: Tuple of exception types that trigger a retry.

    Returns:
        Decorated function with retry logic.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        print(f"❌ Failed after {max_retries + 1} attempts: {e}")
                        raise
                    print(
                        f"⚠️  Attempt {attempt + 1}/{max_retries + 1} failed: {e}"
                    )
                    print(f"   Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            return None

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
#  Initialise rate limiters
# ---------------------------------------------------------------------------
_pubmed_limiter = RateLimiter(**RATE_LIMIT_CONFIG["pubmed"])
_openalex_limiter = RateLimiter(**RATE_LIMIT_CONFIG["openalex"])


# ===================================================================
#  PubMed API – real XML parsing
# ===================================================================

def _parse_pubmed_efetch_xml(xml_text: str) -> List[Dict[str, Any]]:
    """
    Parse the XML response from PubMed's efetch endpoint into records.

    Extracts PMID, title, authors, abstract, journal, year, volume,
    issue, pagination, keywords, MeSH terms, language, and document type.

    Args:
        xml_text: Raw XML string from ``efetch.fcgi?retmode=xml``.

    Returns:
        A list of dicts, one per article, using PubMed field names
        ready for the ``PUBMED`` source mapping in ``etl.py``.
    """
    records = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"Warning: failed to parse PubMed XML: {e}")
        return records

    # Handle both PubmedArticleSet wrapper and single PubmedArticle
    articles = root.findall(".//PubmedArticle")
    if not articles:
        articles = [root] if root.tag == "PubmedArticle" else []

    for article in articles:
        rec: Dict[str, Any] = {}

        # PMID
        pmid_elem = article.find(".//PMID")
        if pmid_elem is not None and pmid_elem.text:
            rec["PMID"] = pmid_elem.text.strip()

        medline = article.find(".//MedlineCitation")
        art = article.find(".//Article") or (medline.find("Article") if medline is not None else None)

        if art is None:
            if "PMID" in rec:
                records.append(rec)
            continue

        # Title
        title_elem = art.find("ArticleTitle")
        if title_elem is not None:
            # Handle mixed-content elements (with sub-elements like <i>)
            rec["TI"] = "".join(title_elem.itertext()).strip()

        # Abstract
        abstract_elem = art.find("Abstract")
        if abstract_elem is not None:
            parts = []
            for at in abstract_elem.findall("AbstractText"):
                text = "".join(at.itertext()).strip()
                if text:
                    parts.append(text)
            rec["AB"] = " ".join(parts)

        # Language
        lang = art.find("Language")
        if lang is not None and lang.text:
            rec["LA"] = lang.text.strip()

        # Publication Type
        pub_types = art.find("PublicationTypeList")
        if pub_types is not None:
            pts = [pt.text.strip() for pt in pub_types.findall("PublicationType") if pt.text]
            rec["PT"] = ";".join(pts)

        # Authors
        author_list = art.find("AuthorList")
        if author_list is not None:
            au_short = []   # Surname Initials
            au_full = []    # Surname, Firstname
            for auth in author_list.findall("Author"):
                last = auth.find("LastName")
                initials = auth.find("Initials")
                fore = auth.find("ForeName")
                if last is not None and last.text:
                    surname = last.text.strip()
                    if initials is not None and initials.text:
                        au_short.append(f"{surname} {initials.text.strip()}")
                    else:
                        au_short.append(surname)
                    if fore is not None and fore.text:
                        au_full.append(f"{surname}, {fore.text.strip()}")
                    else:
                        au_full.append(surname)

                # Affiliations from within author element
                for aff in auth.findall("AffiliationInfo/Affiliation"):
                    if aff.text:
                        if "AD" not in rec:
                            rec["AD"] = aff.text.strip()
                        else:
                            rec["AD"] += ";" + aff.text.strip()

            rec["AU"] = ";".join(au_short)
            rec["FAU"] = ";".join(au_full)

        # Journal
        journal = art.find("Journal")
        if journal is not None:
            jt = journal.find("Title")
            if jt is not None and jt.text:
                rec["JT"] = jt.text.strip()
            ji = journal.find("ISOAbbreviation")
            if ji is not None and ji.text:
                rec["TA"] = ji.text.strip()

            jissue = journal.find("JournalIssue")
            if jissue is not None:
                vol = jissue.find("Volume")
                if vol is not None and vol.text:
                    rec["VI"] = vol.text.strip()
                iss = jissue.find("Issue")
                if iss is not None and iss.text:
                    rec["IP"] = iss.text.strip()
                pub_date = jissue.find("PubDate")
                if pub_date is not None:
                    year = pub_date.find("Year")
                    if year is not None and year.text:
                        rec["DP"] = year.text.strip()
                    else:
                        medline_date = pub_date.find("MedlineDate")
                        if medline_date is not None and medline_date.text:
                            rec["DP"] = medline_date.text.strip()

        # Pagination
        pagination = art.find("Pagination")
        if pagination is not None:
            pgn = pagination.find("MedlinePgn")
            if pgn is not None and pgn.text:
                rec["PG"] = pgn.text.strip()

        # DOI from ArticleIdList
        id_list = article.find(".//ArticleIdList")
        if id_list is not None:
            for aid in id_list.findall("ArticleId"):
                if aid.get("IdType") == "doi" and aid.text:
                    rec["DOI"] = aid.text.strip()

        # Keywords
        kw_list = art.find("KeywordList") or (medline.find("KeywordList") if medline is not None else None)
        if kw_list is not None:
            kws = [kw.text.strip() for kw in kw_list.findall("Keyword") if kw.text]
            rec["OT"] = ";".join(kws)

        # MeSH terms
        mesh_list = medline.find("MeshHeadingList") if medline is not None else None
        if mesh_list is not None:
            terms = []
            for mh in mesh_list.findall("MeshHeading"):
                desc = mh.find("DescriptorName")
                if desc is not None and desc.text:
                    terms.append(desc.text.strip())
            rec["MH"] = ";".join(terms)

        rec["TC"] = 0
        rec["DB"] = "PUBMED"

        if "PMID" in rec or "TI" in rec:
            records.append(rec)

    return records


@retry_with_backoff()
def retrieve_pubmed(
    query: str,
    max_results: int = 100,
    page_size: int = 100,
    use_rate_limit: bool = True,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    search_field: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve bibliographic data from PubMed via the E-utilities API.

    Performs a two-phase retrieval:
      1. ``esearch`` to discover matching PMIDs with pagination.
      2. ``efetch`` to download full XML records in batches.

    The XML is parsed into dicts with PubMed-native field names that
    the ETL transform stage will rename to WoS tags.

    Args:
        query: PubMed search query (e.g. ``"machine learning"``).
        max_results: Maximum total records to retrieve.
        page_size: Number of PMIDs per search page (max 100 000).
        use_rate_limit: Whether to apply rate limiting.
        from_year: Optional starting year filter.
        to_year: Optional ending year filter.
        search_field: Optional search field (``"title"``, ``"title_abstract"``, ``"author"``).

    Returns:
        A list of bibliographic record dicts.

    Raises:
        requests.RequestException: If the API is unreachable after retries.
    """
    if search_field == "title":
        query = f"({query})[ti]"
    elif search_field == "title_abstract":
        query = f"({query})[tiab]"
    elif search_field == "author":
        query = f"({query})[au]"

    if from_year is not None or to_year is not None:
        fy = from_year if from_year is not None else 1800
        ty = to_year if to_year is not None else 3000
        query = f"({query}) AND ({fy}[dp] : {ty}[dp])"

    all_pmids: List[str] = []
    search_url = f"{PUBMED_BASE_URL}esearch.fcgi"
    retstart = 0

    print(f"🔍 Searching PubMed for: {query}")

    # Phase 1 — collect PMIDs
    while len(all_pmids) < max_results:
        if use_rate_limit:
            _pubmed_limiter.acquire()

        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retstart": retstart,
            "retmax": min(page_size, 100000, max_results - len(all_pmids)),
        }

        print(f"  📄 Fetching PMIDs: {retstart}–{retstart + params['retmax']}")
        resp = requests.get(search_url, params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        sr = data.get("esearchresult", {})
        total_count = int(sr.get("count", 0))
        page_ids = sr.get("idlist", [])

        if not page_ids:
            break

        all_pmids.extend(page_ids)
        print(f"  ✓ Retrieved {len(page_ids)} PMIDs (total: {len(all_pmids)}/{total_count})")

        retstart += len(page_ids)
        if len(all_pmids) >= max_results or len(page_ids) < params["retmax"]:
            break

    all_pmids = all_pmids[:max_results]
    print(f"✅ Found {len(all_pmids)} PMIDs to fetch")

    if not all_pmids:
        return []

    # Phase 2 — fetch full records in batches
    all_records: List[Dict[str, Any]] = []
    fetch_url = f"{PUBMED_BASE_URL}efetch.fcgi"
    batch_size = min(200, len(all_pmids))

    for i in range(0, len(all_pmids), batch_size):
        if use_rate_limit:
            _pubmed_limiter.acquire()

        batch = all_pmids[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_pmids) + batch_size - 1) // batch_size

        print(f"📥 Fetching batch {batch_num}/{total_batches} ({len(batch)} records)...")

        resp = requests.get(
            fetch_url,
            params={"db": "pubmed", "id": ",".join(batch), "retmode": "xml"},
            timeout=60,
        )
        resp.raise_for_status()

        # Parse real XML
        batch_records = _parse_pubmed_efetch_xml(resp.text)
        all_records.extend(batch_records)
        print(f"  ✓ Parsed {len(batch_records)} records")

    print(f"📊 Retrieved {len(all_records)} records from PubMed")
    return all_records


# ===================================================================
#  OpenAlex API – comprehensive field extraction
# ===================================================================

@retry_with_backoff()
def retrieve_openalex(
    query: str,
    max_results: int = 100,
    page_size: int = 50,
    use_rate_limit: bool = True,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    search_field: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve bibliographic data from the OpenAlex REST API.

    Extracts all fields required by the WoS schema, including affiliations,
    cited references, keywords, and full bibliographic metadata.

    Args:
        query: Search query string.
        max_results: Maximum total records to retrieve.
        page_size: Results per page (max 200 for OpenAlex).
        use_rate_limit: Whether to apply rate limiting.
        from_year: Optional starting year filter.
        to_year: Optional ending year filter.
        search_field: Optional search field (``"title"``, ``"title_abstract"``, ``"author"``).

    Returns:
        A list of record dicts with WoS-compatible field names.

    Raises:
        requests.RequestException: If the API is unreachable after retries.
    """
    url = f"{OPENALEX_BASE_URL}works"
    all_results: List[Dict[str, Any]] = []
    page = 1
    page_size = min(page_size, 200)

    print(f"🔍 Searching OpenAlex for: {query} [Field: {search_field}]")

    while len(all_results) < max_results:
        if use_rate_limit:
            _openalex_limiter.acquire()

        per_page = min(page_size, max_results - len(all_results))
        params = {"per-page": per_page, "page": page}

        # Add publication year and search field filters if provided
        filters = []
        
        if search_field == "title":
            filters.append(f"title.search:{query}")
        elif search_field == "title_abstract":
            filters.append(f"title_and_abstract.search:{query}")
        else:
            params["search"] = query

        if from_year is not None and to_year is not None:
            filters.append(f"publication_year:{from_year}-{to_year}")
        elif from_year is not None:
            filters.append(f"publication_year:>={from_year}")
        elif to_year is not None:
            filters.append(f"publication_year:<={to_year}")

        if filters:
            params["filter"] = ",".join(filters)

        print(f"  📄 Fetching page {page} ({per_page} records)...")
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()

        works = resp.json().get("results", [])
        if not works:
            print(f"  ✓ No more results at page {page}")
            break

        for work in works:
            if len(all_results) >= max_results:
                break

            # --- Authors (AU short + AF full) ---
            au_short, af_full, affiliations = [], [], []
            for authorship in work.get("authorships", []):
                author_obj = authorship.get("author", {})
                name = author_obj.get("display_name", "")
                if name:
                    af_full.append(name)
                    # Generate short name: last word as surname + initials
                    parts = name.split()
                    if len(parts) >= 2:
                        surname = parts[-1]
                        initials = "".join(p[0] for p in parts[:-1])
                        au_short.append(f"{surname} {initials}")
                    else:
                        au_short.append(name)

                # Institutions → affiliations
                for inst in authorship.get("institutions", []):
                    inst_name = inst.get("display_name", "")
                    if inst_name and inst_name not in affiliations:
                        affiliations.append(inst_name)

            # --- Cited references ---
            ref_ids = work.get("referenced_works", [])
            cr_list = [ref_id.split("/")[-1] for ref_id in ref_ids if ref_id]

            # --- Keywords ---
            keywords = [
                kw.get("display_name", "")
                for kw in work.get("keywords", [])
                if kw.get("display_name")
            ]

            # --- Concepts / topics (→ Index Keywords) ---
            concepts = []
            for topic in work.get("topics", []):
                if topic.get("display_name"):
                    concepts.append(topic["display_name"])
            if not concepts:
                # Fallback to concepts field
                for concept in work.get("concepts", []):
                    if concept.get("display_name"):
                        concepts.append(concept["display_name"])

            # --- Source / journal ---
            # OpenAlex v2 uses primary_location.source
            source_obj = {}
            primary = work.get("primary_location", {})
            if primary:
                source_obj = primary.get("source", {}) or {}
            # Fallback to legacy host_venue
            if not source_obj:
                source_obj = work.get("host_venue", {}) or {}

            journal_name = source_obj.get("display_name", "")
            journal_abbrev = source_obj.get("abbreviated_title", "")

            # --- Biblio metadata ---
            biblio = work.get("biblio", {}) or {}

            # --- DOI ---
            doi = work.get("doi", "") or ""
            if doi.startswith("https://doi.org/"):
                doi = doi[len("https://doi.org/"):]

            # --- Corresponding author ---
            rp = ""
            for authorship in work.get("authorships", []):
                if authorship.get("is_corresponding", False):
                    a = authorship.get("author", {})
                    rp = a.get("display_name", "")
                    insts = authorship.get("institutions", [])
                    if insts:
                        rp += ", " + insts[0].get("display_name", "")
                    break

            result = {
                "UT": work.get("id", "").split("/")[-1],
                "DI": doi,
                "TI": work.get("title", "") or "",
                "AU": ";".join(au_short) if au_short else "",
                "AF": ";".join(af_full) if af_full else "",
                "C1": ";".join(affiliations) if affiliations else "",
                "RP": rp,
                "PY": str(work.get("publication_year", "")),
                "SO": journal_name,
                "JI": journal_abbrev,
                "AB": work.get("abstract", "") or "",
                "TC": work.get("cited_by_count", 0),
                "CR": ";".join(cr_list) if cr_list else "",
                "DE": ";".join(keywords) if keywords else "",
                "ID": ";".join(concepts) if concepts else "",
                "DT": work.get("type", ""),
                "LA": work.get("language", ""),
                "VL": str(biblio.get("volume", "") or ""),
                "IS": str(biblio.get("issue", "") or ""),
                "BP": str(biblio.get("first_page", "") or ""),
                "EP": str(biblio.get("last_page", "") or ""),
                "DB": "OPENALEX",
            }
            all_results.append(result)

        print(f"  ✓ Retrieved {len(works)} records (total: {len(all_results)})")

        if len(works) < per_page:
            break
        page += 1

    print(f"📊 Retrieved {len(all_results)} records from OpenAlex")
    return all_results


# ===================================================================
#  API ETL Pipeline
# ===================================================================

def api_etl_pipeline(
    source: str,
    query: str,
    max_results: int = 100,
    output_path: Optional[str] = None,
    page_size: Optional[int] = None,
    use_rate_limit: bool = True,
    retry_config: Optional[Dict[str, Any]] = None,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    search_field: Optional[str] = None,
) -> pd.DataFrame:
    """
    Complete API-based ETL pipeline with pagination, rate limiting, and retries.

    Retrieves data from PubMed or OpenAlex, then pipes it through the same
    ``transform`` → ``validate`` → ``add_sr`` → ``load`` chain as the
    file-based pipeline.  **No logic is duplicated.**

    Args:
        source: API source — ``"PUBMED"`` or ``"OPENALEX"``.
        query: Free-text search query.
        max_results: Maximum records to retrieve.
        output_path: Optional path to save the standardised CSV.
        page_size: Results per API page (uses defaults if ``None``).
        use_rate_limit: Enable token-bucket rate limiting (default ``True``).
        retry_config: Optional dict overriding ``RETRY_CONFIG``.
        from_year: Optional starting year filter.
        to_year: Optional ending year filter.
        search_field: Optional search field (``"title"``, ``"title_abstract"``, ``"author"``).

    Returns:
        A standardised pandas DataFrame.

    Raises:
        ValueError: If ``source`` is not ``PUBMED`` or ``OPENALEX``.
        requests.RequestException: If API calls fail after retries.
    """
    print(f"\n{'=' * 60}")
    print("API ETL PIPELINE")
    print(f"{'=' * 60}")
    print(f"Source: {source}")
    print(f"Query: {query}")
    if search_field:
        print(f"Search Field: {search_field}")
    if from_year is not None or to_year is not None:
        print(f"Year Filter: {from_year or ''} - {to_year or ''}")
    print(f"Max Results: {max_results}")
    print(f"Rate Limiting: {'Enabled' if use_rate_limit else 'Disabled'}")
    print(f"{'=' * 60}\n")

    try:
        # EXTRACT from API
        if source.upper() == "PUBMED":
            raw_data = retrieve_pubmed(
                query,
                max_results=max_results,
                page_size=page_size or 100,
                use_rate_limit=use_rate_limit,
                from_year=from_year,
                to_year=to_year,
                search_field=search_field,
            )
        elif source.upper() == "OPENALEX":
            raw_data = retrieve_openalex(
                query,
                max_results=max_results,
                page_size=page_size or 50,
                use_rate_limit=use_rate_limit,
                from_year=from_year,
                to_year=to_year,
                search_field=search_field,
            )
        else:
            raise ValueError(
                f"Unsupported API source: {source}. Use PUBMED or OPENALEX."
            )

        print(f"\n✅ API retrieval complete: {len(raw_data)} records fetched\n")

        # TRANSFORM
        print("🔄 Transforming data...")
        df = transform(raw_data, source)
        print(f"✅ Transformed to {len(df.columns)} columns\n")

        # VALIDATE
        print("✓ Validating data...")
        df = validate(df)
        print("✅ Validation complete\n")

        # CALCULATED FIELDS
        print("✓ Generating Short References (SR)...")
        df = add_sr(df)
        print("✅ SR generated\n")

        # LOAD
        if output_path:
            print(f"💾 Saving to {output_path}...")
            df = load(df, output_path)
            print("✅ Saved successfully\n")

        print(f"{'=' * 60}")
        print("PIPELINE COMPLETE")
        print(f"{'=' * 60}")
        print(f"Records: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        print(f"{'=' * 60}\n")

        return df

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}\n")
        raise


# ===================================================================
#  Batch retrieval helper
# ===================================================================

def batch_retrieve_pubmed(
    queries: List[str],
    max_results_per_query: int = 50,
    output_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    Retrieve data for multiple PubMed queries with rate limiting.

    Args:
        queries: List of search query strings.
        max_results_per_query: Max results per query.
        output_dir: Optional directory to save individual CSV files.

    Returns:
        Combined DataFrame with all results.
    """
    all_dfs = []

    print(f"\n{'=' * 60}")
    print("BATCH PUBMED RETRIEVAL")
    print(f"{'=' * 60}")
    print(f"Queries: {len(queries)}")
    print(f"Results per query: {max_results_per_query}")
    print(f"{'=' * 60}\n")

    for i, query in enumerate(queries):
        print(f"\n[{i + 1}/{len(queries)}] Processing: {query}")
        try:
            df = api_etl_pipeline(
                "PUBMED",
                query,
                max_results=max_results_per_query,
                output_path=f"{output_dir}/query_{i}.csv" if output_dir else None,
                use_rate_limit=True,
            )
            all_dfs.append(df)
            if i < len(queries) - 1:
                wait_time = 5
                print(f"⏳ Waiting {wait_time}s before next query...")
                time.sleep(wait_time)
        except Exception as e:
            print(f"⚠️  Query failed: {e}")
            continue

    if not all_dfs:
        print("❌ No data retrieved")
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)

    print(f"\n{'=' * 60}")
    print("BATCH COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total Records: {len(combined)}")
    print(f"{'=' * 60}\n")

    return combined