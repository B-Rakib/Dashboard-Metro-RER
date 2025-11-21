import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- CONFIGURATION ---
st.set_page_config(
    page_title="RATP Traffic 360",
    page_icon="🚇",
    layout="wide"
)

# --- CONSTANTES & STYLE ---
FILE_PATH = r"trafic-annuel-entrant-par-station-du-reseau-ferre-2021.csv"

# Palette RATP Officielle (Jade, Bleu, etc.)
RATP_COLORS = {
    "Métro": "#00A59B",  # Jade
    "RER": "#E3051C",    # Rouge RER A
    "Tramway": "#708D81", # Vert Tram
    "Val": "#009099",
    "Inconnu": "#95A5A6",
    "Autre": "#95A5A6"
}

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=3600)
def load_data():
    if not os.path.exists(FILE_PATH):
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(FILE_PATH, sep=';', encoding='utf-8')
    except:
        return pd.DataFrame()

    # Nettoyage noms colonnes
    df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]

    # Mapping auto
    def get_col(keys):
        for c in df.columns:
            if any(k in c for k in keys): return c
        return None

    mapping = {
        'Reseau': get_col(['reseau', 'réseau']),
        'Station': get_col(['station', 'nom']),
        'Trafic': get_col(['trafic', 'validations']),
        'Ville': get_col(['ville', 'commune']),
        'Arr': get_col(['arrondissement'])
    }
    
    # Renommage
    final_cols = {v: k for k, v in mapping.items() if v}
    df = df.rename(columns=final_cols)

    # Nettoyage Trafic (suppression espaces)
    if 'Trafic' in df.columns:
        df['Trafic'] = df['Trafic'].astype(str).str.replace(r'\s+', '', regex=True)
        df['Trafic'] = pd.to_numeric(df['Trafic'], errors='coerce').fillna(0).astype(int)

    # Nettoyage Localisation
    if 'Ville' in df.columns:
        df['Ville'] = df['Ville'].fillna("Inconnue").str.title()
    
    if 'Reseau' in df.columns:
        df['Reseau'] = df['Reseau'].fillna("Autre").str.replace('Metro', 'Métro')

    return df

# --- FONCTIONS VISUELLES ---

def plot_sunburst(df):
    """Vue hiérarchique : Réseau > Ville > Station"""
    # On prend le top 100 pour éviter un graphique illisible
    top_df = df.sort_values('Trafic', ascending=False).head(100)
    fig = px.sunburst(
        top_df, 
        path=['Reseau', 'Ville', 'Station'], 
        values='Trafic',
        color='Reseau',
        color_discrete_map=RATP_COLORS,
        title="🌌 Répartition Hiérarchique (Zoomable)"
    )
    fig.update_layout(margin=dict(t=40, l=0, r=0, b=0))
    return fig

def plot_top_bar(df):
    """Top 15 Stations"""
    top = df.nlargest(15, 'Trafic')
    fig = px.bar(
        top, x='Trafic', y='Station', orientation='h',
        color='Reseau', color_discrete_map=RATP_COLORS,
        text_auto='.2s', title="🏆 Top 15 Stations"
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
    return fig

def plot_donut(df):
    """Part de marché par Réseau"""
    grp = df.groupby('Reseau')['Trafic'].sum().reset_index()
    fig = px.pie(
        grp, values='Trafic', names='Reseau', hole=0.6,
        color='Reseau', color_discrete_map=RATP_COLORS,
        title="🍩 Part du Trafic par Réseau"
    )
    return fig

def plot_boxplot(df):
    """Distribution et valeurs extrêmes (Outliers)"""
    fig = px.box(
        df, x='Reseau', y='Trafic', color='Reseau',
        color_discrete_map=RATP_COLORS, points='outliers',
        title="📦 Dispersion du Trafic (Échelle Log)", log_y=True
    )
    return fig

def plot_treemap_cities(df):
    """Poids des Villes"""
    grp = df.groupby(['Ville', 'Reseau'])['Trafic'].sum().reset_index()
    top_grp = grp.sort_values('Trafic', ascending=False).head(30)
    fig = px.treemap(
        top_grp, path=['Ville', 'Reseau'], values='Trafic',
        color='Reseau', color_discrete_map=RATP_COLORS,
        title="🏙️ Top Villes par Volume"
    )
    return fig

# --- MAIN APP ---
def main():
    # 1. Style CSS RATP (Jade & Bleu)
    st.markdown("""
        <style>
        .stApp {background-color: #FAFAFA;}
        h1 {color: #00A59B;}
        div[data-testid="stMetricValue"] {color: #2A4394;}
        </style>
        """, unsafe_allow_html=True)
    
    st.title("🚇 Dashboard RATP - Analyse Trafic 2021")
    
    # 2. Chargement
    df = load_data()
    if df.empty:
        st.error(f"❌ Données introuvables : {FILE_PATH}")
        return

    # 3. Sidebar Filtres
    st.sidebar.header("⚙️ Filtres")
    
    # Filtre Réseau
    sel_res = st.sidebar.multiselect(
        "Réseau", 
        df['Reseau'].unique(), 
        default=df['Reseau'].unique()
    )
    
    # Filtre Ville
    cities = sorted(df['Ville'].unique())
    sel_city = st.sidebar.multiselect("Ville", cities)
    
    # Logique de filtrage
    df_viz = df[df['Reseau'].isin(sel_res)]
    if sel_city:
        df_viz = df_viz[df_viz['Ville'].isin(sel_city)]

    # 4. KPIs (Indicateurs Clés)
    k1, k2, k3, k4 = st.columns(4)
    
    total = df_viz['Trafic'].sum()
    k1.metric("Trafic Total", f"{total:,.0f}".replace(",", " "))
    
    k2.metric("Stations", len(df_viz))
    
    top_s = df_viz.loc[df_viz['Trafic'].idxmax()] if not df_viz.empty else None
    k3.metric("Top Station", top_s['Station'] if top_s is not None else "-")
    
    avg = df_viz['Trafic'].mean()
    k4.metric("Moyenne / Station", f"{avg:,.0f}".replace(",", " "))
    
    st.divider()

    # 5. Grille de Visualisation
    
    # Ligne 1 : Sunburst + Top Bar
    c1, c2 = st.columns([1, 1])
    with c1: st.plotly_chart(plot_sunburst(df_viz), use_container_width=True)
    with c2: st.plotly_chart(plot_top_bar(df_viz), use_container_width=True)
    
    # Ligne 2 : Donut + BoxPlot
    c3, c4 = st.columns([1, 2])
    with c3: st.plotly_chart(plot_donut(df_viz), use_container_width=True)
    with c4: st.plotly_chart(plot_boxplot(df_viz), use_container_width=True)
    
    # Ligne 3 : Treemap
    st.plotly_chart(plot_treemap_cities(df_viz), use_container_width=True)

    # 6. Tableau de données (extensible)
    with st.expander("📄 Données détaillées"):
        st.dataframe(df_viz.sort_values('Trafic', ascending=False), use_container_width=True)

if __name__ == "__main__":

    main()
