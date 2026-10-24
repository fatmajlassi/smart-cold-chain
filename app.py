import streamlit as st
import pandas as pd
import requests
import time

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Dashboard - Chaîne du Froid IoT",
    page_icon="❄️",
    layout="wide"
)

st.title("❄️ Tableau de Bord - Suivi de la Chaîne du Froid")
st.markdown("Surveillance en temps réel des températures de l'ESP32 et des alertes de la chaîne du froid.")

# URL de ton API FastAPI locale
API_URL = "http://127.0.0.1:8000/api/temperatures"

def load_data():
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                # Convertir la colonne timestamp si elle existe
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur de connexion à l'API : {e}")
        return pd.DataFrame()

# Bouton pour actualiser manuellement
if st.button("🔄 Actualiser les données"):
    st.rerun()

# Charger les données
df = load_data()

if not df.empty:
    # Métriques principales en haut de page
    latest_temp = df.iloc[0]["temperature"]
    latest_status = df.iloc[0]["status"]
    latest_device = df.iloc[0]["device_id"]

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Dernière Température", value=f"{latest_temp} °C", delta=f"{latest_temp - 8.0:.1f} °C vs seuil")
    
    with col2:
        if latest_status == "ALERTE":
            st.error(f"Statut : {latest_status}")
        else:
            st.success(f"Statut : {latest_status}")
            
    with col3:
        st.metric(label="Capteur Actif", value=latest_device)

    st.markdown("---")

    # Graphique d'évolution de la température
    st.subheader("📈 Évolution de la Température au fil du temps")
    # Trier par ordre chronologique pour le graphique
    df_sorted = df.sort_values("timestamp", ascending=True)
    st.line_chart(df_sorted.set_index("timestamp")["temperature"])

    # Tableau de l'historique complet
    st.subheader("📋 Historique des Mesures")
    st.dataframe(df, use_container_width=True)

else:
    st.warning("Aucune donnée disponible pour le moment. Assure-toi que l'ESP32 envoie des mesures et que le serveur FastAPI tourne.")