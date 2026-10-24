"""Tests unitaires du calcul de risque (risk.py)."""
from datetime import datetime, timedelta
 
from risk import compute_risk
 
T0 = datetime(2026, 10, 24, 12, 0, 0)
 
 
def series(temps, step_s=30):
    return [{"temperature": t, "timestamp": T0 + timedelta(seconds=i * step_s)}
            for i, t in enumerate(temps)]
 
 
def test_aucune_mesure():
    assert compute_risk([])["level"] == "INCONNU"
 
 
def test_temperature_stable_sous_le_seuil():
    assert compute_risk(series([4.0] * 10))["level"] == "FAIBLE"
 
 
def test_temperature_proche_du_seuil():
    assert compute_risk(series([7.5] * 10))["level"] == "MOYEN"
 
 
def test_depassement_court_est_eleve():
    r = compute_risk(series([4.0] * 10 + [9.0] * 3))     # ~1 minute au-dessus de 8 °C
    assert r["level"] == "ÉLEVÉ"
    assert r["over_minutes"] < 5
 
 
def test_depassement_prolonge_est_critique():
    r = compute_risk(series([4.0] * 3 + [9.0] * 14))     # ~6,5 minutes au-dessus de 8 °C
    assert r["level"] == "CRITIQUE"
    assert r["score"] == 100
    assert r["over_minutes"] >= 5
 
 
def test_tendance_haussiere_prevoit_la_rupture():
    r = compute_risk(series([5.0 + 0.2 * i for i in range(11)]))   # monte de 5 à 7 °C
    assert r["level"] == "ÉLEVÉ"
    assert r["predicted"] > 8
 
 
def test_retour_a_la_normale():
    r = compute_risk(series([9.0] * 5 + [4.0] * 10))
    assert r["level"] == "FAIBLE"
    assert r["over_minutes"] == 0
 