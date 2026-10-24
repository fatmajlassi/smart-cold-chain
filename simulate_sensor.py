import time
import random
import requests
import urllib3

# Désactive les avertissements SSL pour le test local
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# L'URL de ton API déployée sur Render
URL = "https://smart-cold-chain-m3el.onrender.com/api/temperature"

print("🚀 Démarrage du simulateur de capteur IoT...")

while True:
    try:
        # Génère une température aléatoire (parfois normale, parfois critique > 8°C pour tester l'alerte)
        temp = round(random.uniform(3.0, 10.5), 2)
        humidity = round(random.uniform(50.0, 75.0), 2)
        
        payload = {
            "temperature": temp,
            "humidity": humidity,
            "device_id": "esp32_simulator_01"
        }
        
        # Envoie la requête POST vers ton API Render (verify=False contourne le souci SSL local)
        response = requests.post(URL, json=payload, verify=False)
        
        if response.status_code == 200 or response.status_code == 201:
            print(f"✅ Données envoyées : {payload} | Réponse : {response.status_code}")
        else:
            print(f"⚠️ Erreur d'envoi : {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Erreur de connexion : {e}")
        
    # Attend 30 secondes avant la prochaine mesure
    time.sleep(30)