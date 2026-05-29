from www.services import *


def get_countries_production(df):
    """
    Generate a choropleth map and table of the countries' scientific production.
    
    Args:
        df: A DataFrame object containing the data.
    
    Returns:
        A Plotly figure object representing the countries' scientific production and a DataFrame of the countries' scientific production.
    """
    # Assicurati che i metadati siano stati estratti
    df = metaTagExtraction(df, "AU_CO")
    df = df.get()

    # Conta le occorrenze dei paesi
    df["AU_CO"] = df["AU_CO"].apply(lambda x: x if isinstance(x, list) else [x])
    df = df.explode("AU_CO")
    df = df[df["AU_CO"].notna() & (df["AU_CO"].astype(str).str.strip() != "") & (df["AU_CO"].astype(str).str.upper() != "NA")]

    # Guard: no country data (e.g. Lens without affiliations)
    if df.empty:
        empty_tab = pd.DataFrame(columns=["Nations", "Freq"])
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(
                text="Country data not available for this database.<br>Affiliation/address fields are required to extract countries.",
                x=0.5, y=0.5, showarrow=False, font=dict(size=15), align="center"
            )],
            plot_bgcolor='white', height=300
        )
        fig = go.FigureWidget(fig)
        fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'], 'displaylogo': False}
        return fig, empty_tab

    # Funzione per normalizzare i nomi dei paesi
    def clean_country_names(country):
        corrections = {
            "USA": "UNITED STATES OF AMERICA",
        }
        return corrections.get(str(country).upper().strip(), str(country).upper().strip())

    # Pulizia e normalizzazione dei nomi in AU_CO
    df["AU_CO"] = df["AU_CO"].apply(clean_country_names)

    # Calcola la frequenza dei paesi
    country_counts = df["AU_CO"].value_counts().reset_index()
    country_counts.columns = ["Tab", "Freq"]

    # Scarica e carica i confini dei paesi
    url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
    world = gpd.read_file(url)

    # Normalizza i nomi dei paesi nel GeoDataFrame
    world['Nations'] = world['SOVEREIGNT'].str.upper().str.strip()

    # Aggrega le geometrie per paese (elimina le geometrie multiple per lo stesso paese)
    world = world.dissolve(by="Nations").reset_index()

    # Unisci i dati dei paesi con le frequenze
    country_prod = world.merge(country_counts, how='left', left_on='Nations', right_on='Tab')

    # Rimuovi duplicati (se ci sono paesi ripetuti)
    country_prod = country_prod.drop_duplicates(subset=['Nations'])

    # Sostituisci i NaN con 0 per la visualizzazione
    country_prod["Freq"] = country_prod["Freq"].fillna(0)

    # Converte il GeoDataFrame in GeoJSON
    geojson_data = country_prod.__geo_interface__

    # Crea una mappa interattiva con Plotly
    fig = px.choropleth(
        country_prod,
        geojson=geojson_data,
        locations='Nations',
        featureidkey="properties.Nations",  # Assicurati che il nome coincida con il GeoJSON
        color='Freq',
        hover_name='Nations',
        hover_data={'Freq': True},
        color_continuous_scale=px.colors.sequential.Blues,
        labels={'Freq': 'N. documents'}
    )

    # Configurazione della mappa
    fig.update_geos(
        showcoastlines=False,
        showland=True,
        landcolor="white",
        showcountries=False,
        countrycolor="white",
        fitbounds="locations",  # Impedisce il pan
        visible=False  # Disabilita la visibilità dei controlli di pan
    )

    # Configurazione del layout
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        title=None,
        height=800,  # Imposta l'altezza della mappa
        geo=dict(
            lakecolor='white',
            projection_scale=1,  # Rendi la mappa fissa
            framecolor='white'  # Rimuovi il riquadro
        ),
        coloraxis_showscale=True,  # Aggiungi la legenda
        coloraxis=dict(
            colorbar=dict(
                orientation='h',  # Imposta la legenda in orizzontale
                yanchor='bottom',
                y=-0.2,  # Posiziona la legenda in basso
                xanchor='center',
                x=0.5
            )
        )
    )

    # Modifica i dati di hover per mostrare "N. documents"
    fig.update_traces(
        hovertemplate='<b>%{hovertext}</b><br>N. documents: %{z}<extra></extra>',
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),
    )
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}

    # Crea una tabella aggregata per l'output
    tab = country_prod[['Nations', 'Freq']].sort_values(by='Freq', ascending=False)

    return fig, tab
