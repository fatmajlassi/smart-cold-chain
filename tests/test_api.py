"""Tests d'intégration de l'API (MongoDB et Firebase remplacés par des simulacres)."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
 
import pytest
from fastapi.testclient import TestClient
 
import main
 
 
@pytest.fixture
def api(monkeypatch):
    fake_collection = SimpleNamespace(
        insert_one=AsyncMock(return_value=SimpleNamespace(inserted_id="abc123")))
    monkeypatch.setattr(main, "temperature_collection", fake_collection)
    monkeypatch.setattr(main, "push_live", AsyncMock(return_value=False))
    return TestClient(main.app), fake_collection
 
 
def saved(fake, call=-1):
    return fake.insert_one.await_args_list[call].args[0]
 
 
def test_racine(api):
    client, _ = api
    assert client.get("/").status_code == 200
 
 
def test_temperature_normale(api):
    client, fake = api
    r = client.post("/api/temperature", json={"temperature": 5.0, "device_id": "esp32"})
    assert r.status_code == 200
    assert r.json()["temperature_status"] == "NORMAL"
    assert saved(fake)["transport_id"] == "TRANSPORT_1"
 
 
def test_temperature_au_dessus_du_seuil(api):
    client, _ = api
    r = client.post("/api/temperature", json={"temperature": 9.0, "device_id": "esp32"})
    assert r.json()["temperature_status"] == "ALERTE"
 
 
def test_le_seuil_exact_n_est_pas_une_alerte(api):
    client, _ = api
    r = client.post("/api/temperature", json={"temperature": 8.0, "device_id": "esp32"})
    assert r.json()["temperature_status"] == "NORMAL"
 
 
@pytest.mark.parametrize("payload", [
    {"temperature": 500, "device_id": "esp32"},                 # valeur impossible
    {"temperature": "abc", "device_id": "esp32"},               # mauvais type
    {"temperature": 5.0},                                       # device_id manquant
    {"temperature": 5.0, "device_id": "esp32", "lat": 123},     # latitude hors limites
    {"temperature": 5.0, "device_id": "esp32", "lon": 200},     # longitude hors limites
    {"temperature": 5.0, "device_id": "esp32", "humidity": 150},
])
def test_donnees_invalides_refusees(api, payload):
    client, fake = api
    assert client.post("/api/temperature", json=payload).status_code == 422
    fake.insert_one.assert_not_awaited()                        # rien n'est enregistré
 
 
def test_gps_et_transport_sont_enregistres(api):
    client, fake = api
    client.post("/api/temperature", json={
        "temperature": 5.0, "device_id": "esp32",
        "transport_id": "TR-001", "lat": 36.8065, "lon": 10.1815})
    rec = saved(fake)
    assert (rec["transport_id"], rec["lat"], rec["lon"]) == ("TR-001", 36.8065, 10.1815)
 
 
def test_horodatage_utc_converti(api):
    client, fake = api
    client.post("/api/temperature", json={
        "temperature": 5.0, "device_id": "esp32", "timestamp": "2026-10-24T15:27:12Z"})
    assert saved(fake)["timestamp"] == datetime(2026, 10, 24, 15, 27, 12)
 
 
def test_reprise_apres_coupure_reseau(api):
    """Après une coupure, l'ESP32 renvoie ses mesures en attente avec leur heure d'origine."""
    client, fake = api
    heures = ["2026-10-24T15:00:00Z", "2026-10-24T15:00:30Z", "2026-10-24T15:01:00Z"]
    for h in heures:
        r = client.post("/api/temperature", json={
            "temperature": 6.0, "device_id": "esp32", "transport_id": "TR-001", "timestamp": h})
        assert r.status_code == 200
    assert fake.insert_one.await_count == 3
    stamps = [saved(fake, i)["timestamp"] for i in range(3)]
    assert stamps == sorted(stamps)                              # ordre d'origine conservé
    assert stamps[0] == datetime(2026, 10, 24, 15, 0, 0)         # et non l'heure de réception
 