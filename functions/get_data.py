"""
Dashboard Data Import Handler
==============================

This module bridges the Shiny dashboard's file upload workflow with the
new ETL pipeline.  When the user uploads a raw file, the data is processed
through the unified ETL chain: **Extract → Transform → Validate → Load**,
producing a source-agnostic DataFrame that all downstream analytical
functions can consume without crashing.

The legacy ``biblio_json()`` path is retained as a fallback for formats
not yet handled by the ETL pipeline (e.g., BibTeX, ZIP archives, R Data).
"""

from www.services import *


# ---------------------------------------------------------------------------
#  Mapping from Shiny dropdown values to ETL source identifiers
# ---------------------------------------------------------------------------
_DASHBOARD_SOURCE_MAP = {
    "wos": "WEB_OF_SCIENCE",
    "scopus": "SCOPUS",
    "dimensions": "DIMENSIONS",
    "pubmed": "PUBMED",
    "cochrane": "COCHRANE",
    "lens": "LENS",
}


def _apply_etl_standardisation(raw_df, etl_source):
    """
    Apply the ETL Transform → Validate → Add_SR pipeline to a raw DataFrame.

    This function is used both for direct ETL-extracted data and for
    data that was initially loaded via the legacy ``biblio_json()`` path.
    It ensures the downstream analytical functions always receive a
    properly standardised DataFrame.

    Args:
        raw_df: A raw pandas DataFrame (e.g., from ``pd.read_json``
            or from ``etl_pipeline``).
        etl_source: The ETL source identifier (e.g. ``"SCOPUS"``).

    Returns:
        A standardised pandas DataFrame.
    """
    from www.services.etl import transform, validate, add_sr

    # Convert DataFrame rows to list-of-dicts for the transform stage
    records = raw_df.to_dict(orient="records")
    df_std = transform(records, etl_source)
    df_std = validate(df_std)
    df_std = add_sr(df_std)
    return df_std


def get_data(input, database, df, reset_callback=None):
    """
    Handle the data upload and processing for the Shiny dashboard.

    This function intercepts file uploads from the UI, detects the source
    database, and routes the data through the **ETL pipeline** for
    standardisation.  The resulting DataFrame conforms to the WoS internal
    schema and is compatible with all analytical functions.

    For file formats handled by the ETL pipeline (CSV, XLSX, TXT, CIW),
    the data is processed directly via ``etl_pipeline()``.  For legacy
    formats (BibTeX, ZIP, R Data), the original ``biblio_json()`` path is
    used followed by an ETL standardisation pass.

    Args:
        input: Shiny input object providing user-selected values such as
            ``input.Dataset()``, ``input.database()``, ``input.author()``.
        database: Human-readable database name (e.g. ``"Scopus"``).
        df: A ``reactive.Value`` container for the DataFrame.
        reset_callback: Optional callable invoked when a new dataset is
            loaded, to reset cached analysis results.

    Returns:
        A Shiny UI element indicating the status of the data import.
    """
    file: list[FileInfo] | None = input.Dataset()

    if file is None:
        text = ui.h5("Please select a file to begin importing your data.")

    elif input.select() == "1A":
        ui.update_action_button("action_button_save", disabled=False)

        source = input.database()       # e.g. "wos", "scopus"
        author = input.author()
        etl_source = _DASHBOARD_SOURCE_MAP.get(source, source.upper())

        try:
            # Determine if the ETL pipeline can handle the file directly
            file_name = file[0]["name"].lower()
            file_path = file[0]["datapath"]

            # ETL-native formats: CSV, XLSX/XLS, TXT, CIW, XML
            etl_native_extensions = (".csv", ".xlsx", ".xls", ".txt", ".ciw", ".xml")
            is_etl_native = file_name.endswith(etl_native_extensions)

            if is_etl_native and len(file) == 1 and not file_name.endswith(".zip"):
                # ── PRIMARY PATH: ETL pipeline ──
                from www.services.etl import etl_pipeline

                # --- DEBUG LOGGING ---
                try:
                    import pandas as pd
                    if file_path.lower().endswith(('.xlsx', '.xls')):
                        raw_df_first = pd.read_excel(file_path, header=None, nrows=5)
                    else:
                        raw_df_first = pd.read_csv(file_path, header=None, nrows=5)
                    
                    with open("/home/badawy/uni_projects/HSBD mod B/bibliometrix-python/debug_upload.txt", "w", encoding="utf-8") as f_debug:
                        f_debug.write(f"File Name: {file_name}\n")
                        f_debug.write(f"Detected Source: {source}\n")
                        f_debug.write(f"ETL Source: {etl_source}\n")
                        f_debug.write(f"Raw first few rows headers:\n{raw_df_first.iloc[:3].to_dict(orient='records')}\n\n")
                except Exception as ex:
                    with open("/home/badawy/uni_projects/HSBD mod B/bibliometrix-python/debug_upload.txt", "w", encoding="utf-8") as f_debug:
                        f_debug.write(f"Failed to log raw rows: {ex}\n")
                # ---------------------

                standardised = etl_pipeline(etl_source, file_path)
                df.set(standardised)

                # --- DEBUG APPEND TRANSFORMED ---
                try:
                    with open("/home/badawy/uni_projects/HSBD mod B/bibliometrix-python/debug_upload.txt", "a", encoding="utf-8") as f_debug:
                        f_debug.write(f"Transformed columns: {standardised.columns.tolist()}\n")
                        non_empty_de = standardised[standardised["DE"].apply(len) > 0]
                        f_debug.write(f"Transformed DE count: {len(non_empty_de)} / {len(standardised)}\n")
                        if len(non_empty_de) > 0:
                            f_debug.write(f"Sample DE values: {non_empty_de['DE'].iloc[0]}\n")
                except Exception as ex:
                    pass
                # --------------------------------

                if reset_callback:
                    reset_callback()

                text = ui.p(
                    f"✅ {database}'s file processed via ETL pipeline. "
                    f"The dataset contains {df.get().shape[0]} rows and "
                    f"{df.get().shape[1]} columns (standardised)."
                )

            elif len(file) > 1:
                # ── MULTIPLE FILES: Legacy path + ETL standardisation ──
                json_data = process_multiple_files(file, source, author)
                raw_df = pd.read_json(StringIO(json_data))
                standardised = _apply_etl_standardisation(raw_df, etl_source)
                df.set(standardised)

                if reset_callback:
                    reset_callback()

                text = ui.p(
                    f"✅ {database}: {len(file)} files processed and combined. "
                    f"The dataset contains {df.get().shape[0]} rows and "
                    f"{df.get().shape[1]} columns (standardised)."
                )

            else:
                # ── FALLBACK: Legacy path + ETL standardisation ──
                # (handles .bib, .zip, and other legacy formats)
                file_type = file[0]["name"]
                json_data = biblio_json(file_path, source, file_type, author)
                raw_df = pd.read_json(StringIO(json_data))
                standardised = _apply_etl_standardisation(raw_df, etl_source)
                df.set(standardised)

                if reset_callback:
                    reset_callback()

                if file_type.endswith(".zip"):
                    text = ui.p(
                        f"✅ {database}'s ZIP archive uploaded and extracted. "
                        f"The dataset contains {df.get().shape[0]} rows and "
                        f"{df.get().shape[1]} columns (standardised)."
                    )
                else:
                    text = ui.p(
                        f"✅ {database}'s file uploaded. "
                        f"The dataset contains {df.get().shape[0]} rows and "
                        f"{df.get().shape[1]} columns (standardised)."
                    )

        except Exception as e:
            text = ui.div(
                ui.h5("Error processing file(s):", style="color: red;"),
                ui.p(str(e), style="color: red;"),
                ui.p(
                    "Please check that your files are in the correct format "
                    "and try again.",
                    style="color: gray;",
                ),
            )

    elif input.select() == "1B":
        # ── Load pre-exported Bibliometrix file ──
        raw_df = pd.read_excel(file[0]["datapath"])
        # Apply ETL standardisation to ensure consistency
        try:
            # Detect source from DB column if present
            if "DB" in raw_df.columns and not raw_df["DB"].empty:
                etl_source = str(raw_df["DB"].iloc[0]).upper()
            else:
                etl_source = "WEB_OF_SCIENCE"  # default
            standardised = _apply_etl_standardisation(raw_df, etl_source)
            df.set(standardised)
        except Exception:
            # If ETL standardisation fails, use raw data as-is
            df.set(raw_df)

        if reset_callback:
            reset_callback()
        text = ui.p(
            f"{database}'s file uploaded successfully! "
            f"The dataset contains {df.get().shape[0]} rows and "
            f"{df.get().shape[1]} columns."
        )

    else:
        text = ""

    return text
