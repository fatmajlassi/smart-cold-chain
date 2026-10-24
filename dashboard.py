import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time

# Configuration de la page
st.set_page_config(
    page_title="Chaîne du Froid - Dashboard IoT",
    page_icon="❄️",
    layout="wide"
)

# Titre principal
st.title("❄️ Monitoring en Temps Réel - Chaîne du Froid")
st.markdown("Suivi des températures et alertes en direct depuis les capteurs IoT.")

# URL de ton API Render
API_URL = "https://smart-cold-chain-m3el.onrender.com/api/temperatures"

# Fonction pour récupérer les données depuis ton API Render
def fetch_data():
    try:
        response = requests.get(API_URL, verify=False)
        if response.status_code == 200:
            res_json = response.json()
            # Si l'API renvoie directement une liste
            if isinstance(res_json, list):
                return pd.DataFrame(res_json)
            # Si l'API renvoie un dictionnaire avec une clé "data"
            elif isinstance(res_json, dict):
                data = res_json.get("data", [])
                return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Erreur de connexion à l'API : {e}")
    return pd.DataFrame()

# Chargement des données
df = fetch_data()

if not df.empty:
    # 1. Cartes de Métriques (KPIs)
    col1, col2, col3 = st.columns(3)
    
    last_temp = df['temperature'].iloc[-1]
    last_humidity = df['humidity'].iloc[-1] if 'humidity' in df.columns else "N/A"
    total_alerts = len(df[df['temperature'] > 8.0])

    col1.metric("Dernière Température", f"{last_temp} °C", delta=f"{round(last_temp - 5.0, 2)} °C vs Seuil")
    col2.metric("Dernière Humidité", f"{last_humidity} %")
    col3.metric("Nombre d'Alertes Critical (> 8°C)", total_alerts, delta_color="inverse")

    # Alerte visuelle si dépassement
    if last_temp > 8.0:
        st.error(f"⚠️ **ALERTE CRITIQUE :** La température actuelle ({last_temp} °C) dépasse le seuil maximal de 8°C !")
    else:
        st.success("✅ Température sous contrôle (Conforme à la chaîne du froid).")

    st.markdown("---")

    # 2. Graphique d'évolution des températures
    st.subheader("📈 Évolution de la Température dans le Temps")
    
    # Création de la courbe interactive avec Plotly
    fig = px.line(
        df, 
        y='temperature', 
        title="Courbe de Température (°C)",
        labels={'index': 'Mesure', 'temperature': 'Température (°C)'},
        markers=True
    )
    
    # Ajout d'une ligne rouge horizontale pour le seuil critique de 8°C
    fig.add_hline(y=8.0, line_dash="dash", line_color="red", annotation_text="Seuil Limite (8°C)")
    
    st.plotly_chart(fig, use_container_width=True)

    # 3. Tableau de données brutes
    with st.expander("📄 Voir l'historique brut des données (JSON/Tableau)"):
        st.dataframe(df.tail(20))

else:
    st.warning("Aucune donnée disponible pour le moment. Assure-toi que ton script `simulate_sensor.py` est en train de tourner.")

# Bouton de rafraîchissement manuel
if st.button("🔄 Rafraîchir les données"):
    st.rerun()