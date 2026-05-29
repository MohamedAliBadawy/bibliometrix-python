from www.services import *


def get_bradford_law(df):
    """
    Generate a plot and table based on Bradford's Law.
    
    Args:
        df: A DataFrame object containing the data.
        
    Returns:
        A Plotly figure object and a DataFrame of the Bradford's Law zones.
    """
    data = df.get()
    
    # Remove duplicates
    data = data.drop_duplicates(subset='SR')
    
    if "SO" not in data.columns or data["SO"].isna().all():
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text="No source data available",
                            x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
            plot_bgcolor='white', height=300
        )
        fig = go.FigureWidget(fig)
        return fig, pd.DataFrame(columns=["SO", "Rank", "Freq", "cumFreq", "Zone"])

    source_counts = data["SO"].str.upper().value_counts()
    
    if len(source_counts) == 0:
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(text="No source data available",
                            x=0.5, y=0.5, showarrow=False, font=dict(size=16))],
            plot_bgcolor='white', height=300
        )
        fig = go.FigureWidget(fig)
        return fig, pd.DataFrame(columns=["SO", "Rank", "Freq", "cumFreq", "Zone"])

    # Total number of articles (equivalent to N in R)
    N = source_counts.sum()
    nSO = len(source_counts)
    
    # Cumulative sum of the frequencies
    cumSO = source_counts.cumsum()
    
    # R equivalents:
    # zone1_end = sum(df$cumFreq <= N/3) + 1
    # zone2_end = sum(df$cumFreq <= 2 * N/3) + 1
    # zone1_end = min(zone1_end, nSO)
    # zone2_end = min(zone2_end, nSO)
    a = (cumSO <= N / 3).sum() + 1
    b = (cumSO <= 2 * N / 3).sum() + 1
    a = min(a, nSO)
    b = min(b, nSO)
    
    Z = ["Zone 3"] * nSO
    for i in range(min(a, nSO)):
        Z[i] = "Zone 1"
    if a < nSO:
        for i in range(a, min(b, nSO)):
            Z[i] = "Zone 2"
            
    df_bradford = pd.DataFrame({
        "SO": cumSO.index,
        "Rank": range(1, nSO + 1),
        "Freq": source_counts.values,
        "cumFreq": cumSO.values,
        "Zone": Z
    })
    
    # Calculate Theoretical curve
    log_rank = np.log(df_bradford["Rank"])
    cum_freq = df_bradford["cumFreq"]
    
    # Linear model fit: cumFreq = intercept + slope * log_rank
    slope, intercept = np.polyfit(log_rank, cum_freq, 1)
    df_bradford["Theoretical"] = intercept + slope * log_rank
    
    # Create the Plotly figure
    fig = go.Figure()
    
    # Calculate boundaries for x-axis in logRank
    xz1 = np.log(a)
    xz2 = np.log(b)
    xmax = np.log(nSO)
    ymax = N
    
    # Add shaded background rects for Zone 1, Zone 2, Zone 3
    # Zone 1
    fig.add_shape(
        type="rect",
        x0=0,
        x1=xz1,
        y0=0,
        y1=ymax,
        fillcolor="#2171B5",
        opacity=0.08,
        line_width=0,
        layer="below"
    )
    # Zone 2
    if a < nSO:
        fig.add_shape(
            type="rect",
            x0=xz1,
            x1=xz2,
            y0=0,
            y1=ymax,
            fillcolor="#6BAED6",
            opacity=0.08,
            line_width=0,
            layer="below"
        )
    # Zone 3
    if b < nSO:
        fig.add_shape(
            type="rect",
            x0=xz2,
            x1=xmax,
            y0=0,
            y1=ymax,
            fillcolor="#BDD7E7",
            opacity=0.08,
            line_width=0,
            layer="below"
        )
        
    # Add vertical dashed lines separating the zones
    fig.add_shape(
        type="line",
        x0=xz1, x1=xz1, y0=0, y1=ymax,
        line=dict(color="#666666", width=1, dash="dash"),
        layer="below"
    )
    if b < nSO:
        fig.add_shape(
            type="line",
            x0=xz2, x1=xz2, y0=0, y1=ymax,
            line=dict(color="#666666", width=1, dash="dash"),
            layer="below"
        )

    # Add zone annotations
    n1 = (df_bradford["Zone"] == "Zone 1").sum()
    n2 = (df_bradford["Zone"] == "Zone 2").sum()
    n3 = (df_bradford["Zone"] == "Zone 3").sum()
    
    fig.add_annotation(
        x=xz1 / 2, y=ymax * 0.92,
        text=f"<b>Core</b><br>({n1} sources)",
        showarrow=False,
        font=dict(size=12, color="#222222", family="Segoe UI, Arial"),
        align="center",
        bgcolor="rgba(255,255,255,0.7)",
        bordercolor="#2171B5",
        borderwidth=1,
        borderpad=4
    )
    if a < nSO:
        fig.add_annotation(
            x=(xz1 + xz2) / 2, y=ymax * 0.92,
            text=f"<b>Zone 2</b><br>({n2} sources)",
            showarrow=False,
            font=dict(size=12, color="#222222", family="Segoe UI, Arial"),
            align="center",
            bgcolor="rgba(255,255,255,0.7)",
            bordercolor="#6BAED6",
            borderwidth=1,
            borderpad=4
        )
    if b < nSO:
        fig.add_annotation(
            x=(xz2 + xmax) / 2, y=ymax * 0.92,
            text=f"<b>Zone 3</b><br>({n3} sources)",
            showarrow=False,
            font=dict(size=12, color="#222222", family="Segoe UI, Arial"),
            align="center",
            bgcolor="rgba(255,255,255,0.7)",
            bordercolor="#BDD7E7",
            borderwidth=1,
            borderpad=4
        )

    # Add Theoretical line (dashed, orange-red)
    fig.add_trace(go.Scatter(
        x=log_rank,
        y=df_bradford["Theoretical"],
        mode='lines',
        name='Theoretical (linear fit)',
        line=dict(color='#D6604D', width=2, dash='dash'),
        hovertemplate="<b>Theoretical Cumulative Articles:</b> %{y:.2f}<extra></extra>"
    ))

    # Add Cumulative Empirical line (solid, black-blue)
    fig.add_trace(go.Scatter(
        x=log_rank,
        y=df_bradford["cumFreq"],
        mode='lines+markers',
        name='Empirical Cumulative Articles',
        marker=dict(
            color='#1A1A1A',
            size=6,
            line=dict(width=1, color='white'),
            opacity=0.6
        ),
        line=dict(color='#1A1A1A', width=1.5),
        hovertemplate=(
            "<b>Source:</b> %{customdata[0]}<br>"
            "<b>Rank:</b> %{customdata[1]}<br>"
            "<b>N. of Articles:</b> %{customdata[2]}<br>"
            "<b>Cumulative Articles:</b> %{y}<br>"
            "<b>Zone:</b> %{customdata[3]}<extra></extra>"
        ),
        customdata=np.stack([df_bradford["SO"], df_bradford["Rank"], df_bradford["Freq"], df_bradford["Zone"]], axis=-1)
    ))

    # Customize Layout
    # Set x-ticks to the Core sources (Zone 1) names for beautiful readability
    tick_indices = list(range(0, min(a, nSO)))
    tick_vals = [log_rank.iloc[i] for i in tick_indices]
    tick_text = [df_bradford["SO"].iloc[i][:25] for i in tick_indices]

    fig.update_layout(
        title=dict(
            text=f"<b>Bradford's Law</b><br><span style='font-size:12px;color:#666666;'>C(r) = {intercept:.1f} + {slope:.1f} * log(r)</span>",
            x=0.5,
            xanchor="center",
            font=dict(size=18, color="#222222")
        ),
        xaxis=dict(
            title="Source log(Rank)",
            tickmode='array',
            tickvals=tick_vals,
            ticktext=tick_text,
            tickangle=90,
            showgrid=True,
            gridcolor="#F0F0F0",
            zeroline=False,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            title="Cumulative N. of Articles",
            showgrid=True,
            gridcolor="#F0F0F0",
            zeroline=False,
            tickfont=dict(size=10),
        ),
        plot_bgcolor='white',
        font=dict(color="#222222", size=11, family="Segoe UI, Arial"),
        margin=dict(l=80, r=40, t=80, b=120),
        height=700,
        showlegend=False,
        hoverlabel=dict(
            bgcolor="white",
            font_size=11,
            font_family="Segoe UI, Arial",
            bordercolor="#5567BB"
        ),
    )
    
    fig = go.FigureWidget(fig)
    fig._config = fig._config | {'modeBarButtonsToRemove': ['pan', 'select', 'lasso2d', 'toImage'],
                                 'displaylogo': False}
    
    # Shorten the source names in the final returned dataframe to 25 characters for display
    df_bradford_out = df_bradford.copy()
    df_bradford_out["SO"] = df_bradford_out["SO"].str[:25]
    
    return fig, df_bradford_out
