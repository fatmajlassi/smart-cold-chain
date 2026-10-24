"""risk.py : logique de risque de rupture de la chaîne du froid (sans dépendance à la base)."""
from datetime import datetime
 
import numpy as np
 
TEMP_MAX = 8.0        # seuil de rupture (°C)
PROLONGED_MIN = 5.0   # dépassement "prolongé" : plus de 5 minutes
HORIZON_MIN = 10.0    # prédiction à 10 minutes
WINDOW = 12           # nombre de mesures utilisées pour la tendance
 
 
def to_dt(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts.replace(tzinfo=None) if ts.tzinfo else ts
    return datetime.fromisoformat(str(ts).replace("Z", "")).replace(tzinfo=None)
 
 
def compute_risk(docs: list[dict]) -> dict:
    """docs : mesures triées par temps croissant (champs temperature, timestamp)."""
    if not docs:
        return {"level": "INCONNU", "score": 0, "message": "Aucune mesure",
                "predicted": None, "slope_per_min": None, "over_minutes": 0}
 
    recent = docs[-WINDOW:]
    times = np.array([to_dt(d["timestamp"]).timestamp() for d in recent])
    temps = np.array([float(d["temperature"]) for d in recent])
    current = float(temps[-1])
 
    # Tendance : régression linéaire sur les dernières mesures (°C par minute)
    slope = 0.0
    if len(recent) >= 3 and times[-1] > times[0]:
        slope = float(np.polyfit(times - times[0], temps, 1)[0]) * 60
    predicted = current + slope * HORIZON_MIN
 
    # Durée du dépassement en cours (mesures consécutives > seuil jusqu'à la dernière)
    over_minutes = 0.0
    run_start = None
    for d in reversed(docs):
        if float(d["temperature"]) > TEMP_MAX:
            run_start = to_dt(d["timestamp"])
        else:
            break
    if run_start is not None:
        over_minutes = (to_dt(docs[-1]["timestamp"]) - run_start).total_seconds() / 60
 
    if current > TEMP_MAX and over_minutes >= PROLONGED_MIN:
        level, score = "CRITIQUE", 100
        msg = f"Rupture de la chaîne du froid : dépassement depuis {over_minutes:.0f} min"
    elif current > TEMP_MAX:
        level, score, msg = "ÉLEVÉ", 85, "Seuil dépassé, surveillance du dépassement"
    elif predicted > TEMP_MAX:
        level, score = "ÉLEVÉ", int(min(80, 50 + (predicted - TEMP_MAX) * 10))
        msg = f"Seuil probablement dépassé dans {HORIZON_MIN:.0f} min ({predicted:.1f} °C prévus)"
    elif current > TEMP_MAX - 1 or slope > 0.15:
        level, score, msg = "MOYEN", 40, "Température proche du seuil ou en hausse"
    else:
        level, score, msg = "FAIBLE", 10, "Chaîne du froid respectée"
 
    return {"level": level, "score": score, "message": msg,
            "predicted": round(predicted, 2), "slope_per_min": round(slope, 3),
            "over_minutes": round(over_minutes, 1)}
 