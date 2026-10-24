"""
simulate_sensor.py : simule un transport Tunis -> Sousse avec GPS, une rupture de température
et une coupure réseau (les mesures sont mémorisées puis renvoyées avec leur heure d'origine).
 
Variables d'environnement (optionnelles) :
    API_URL   (défaut : votre API Render)
    INTERVAL  secondes entre deux mesures (défaut : 5 pour la démo, mettez 30 pour du réaliste)
"""
import os
import random
import time
from datetime import datetime, timezone
 
import requests
 
URL = os.environ.get("API_URL", "https://smart-cold-chain-m3el.onrender.com/api/temperature")
INTERVAL = float(os.environ.get("INTERVAL", 5))
 
DEVICE_ID = "esp32_simulator_01"
TRANSPORT_ID = "TR-" + datetime.now().strftime("%Y%m%d-%H%M")
 
START = (36.8065, 10.1815)   # Tunis
END = (35.8256, 10.6369)     # Sousse
N_STEPS = 60
 
BREACH = range(28, 46)       # étapes où la température dépasse 8 °C
OUTAGE = range(12, 18)       # étapes sans réseau (coupure simulée)
 
buffer: list[dict] = []
 
 
def flush() -> None:
    """Envoie les mesures en attente, dans l'ordre. S'arrête à la première erreur."""
    while buffer:
        try:
            r = requests.post(URL, json=buffer[0], timeout=15)
        except requests.RequestException as e:
            print(f"❌ Réseau indisponible ({e.__class__.__name__}), {len(buffer)} mesure(s) en attente")
            return
        if r.status_code in (200, 201):
            p = buffer.pop(0)
            print(f"✅ Envoyé : {p['temperature']} °C | {p['lat']}, {p['lon']} | reste {len(buffer)} en attente")
        else:
            print(f"⚠️ Erreur d'envoi : {r.status_code} - {r.text}")
            return
 
 
def temperature_at(i: int) -> float:
    if i in BREACH:
        k = i - BREACH.start
        t = 5 + k * 0.6 if k < 10 else 11 - (k - 10) * 0.9      # montée puis retour
    else:
        t = 4.5
    return round(t + random.uniform(-0.6, 0.6), 2)
 
 
print(f"🚀 Transport {TRANSPORT_ID} : démarrage du simulateur")
 
for i in range(N_STEPS):
    k = i / (N_STEPS - 1)
    buffer.append({
        "device_id": DEVICE_ID,
        "transport_id": TRANSPORT_ID,
        "temperature": temperature_at(i),
        "humidity": round(random.uniform(50, 75), 1),
        "lat": round(START[0] + (END[0] - START[0]) * k + random.uniform(-0.002, 0.002), 5),
        "lon": round(START[1] + (END[1] - START[1]) * k + random.uniform(-0.002, 0.002), 5),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
 
    if i in OUTAGE:
        print(f"📡 Coupure réseau simulée (étape {i}) : mesure mémorisée")
    else:
        flush()
 
    time.sleep(INTERVAL)
 
flush()
print("🏁 Transport terminé")
 