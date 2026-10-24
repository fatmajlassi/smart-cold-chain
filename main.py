import os
from datetime import datetime, timezone
from typing import Optional
 
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
 
from risk import TEMP_MAX, WINDOW, compute_risk
 
app = FastAPI(title="Smart Cold Chain API")
 
# Autorise le dashboard HTML (index.html) à appeler l'API
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
 
# Connexion à MongoDB (variable d'environnement sur Render, sinon localhost)
MONGO_DETAILS = os.environ.get("MONGO_DETAILS", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.smart_cold_chain
temperature_collection = database.get_collection("temperatures")
 
DEFAULT_TRANSPORT = "TRANSPORT_1"   # pour les anciennes mesures sans transport_id
 
 
class TemperatureData(BaseModel):
    temperature: float = Field(..., ge=-50, le=100)       # validation des données
    device_id: str = Field(..., min_length=1)
    humidity: Optional[float] = Field(None, ge=0, le=100)
    transport_id: str = DEFAULT_TRANSPORT
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    timestamp: Optional[datetime] = None                  # permet de renvoyer des mesures après une coupure réseau
 
 
# ---------- utilitaires ----------
def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
 
 
def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc["_id"] = str(doc["_id"])
    ts = doc.get("timestamp")
    if isinstance(ts, datetime):
        doc["timestamp"] = ts.isoformat() + "Z"   # "Z" = UTC, sinon le navigateur décale l'heure
    return doc
 
 
def _filter(transport_id: Optional[str]) -> dict:
    if not transport_id:
        return {}
    if transport_id == DEFAULT_TRANSPORT:
        return {"$or": [{"transport_id": DEFAULT_TRANSPORT}, {"transport_id": {"$exists": False}}]}
    return {"transport_id": transport_id}
 
 
# ---------- routes ----------
@app.get("/")
def read_root():
    return {"message": "Smart Cold Chain API is live and running!"}
 
 
@app.post("/api/temperature")
async def receive_temperature(data: TemperatureData):
    print(f"[{data.device_id}] Température reçue : {data.temperature} °C")
 
    # Logique d'alerte côté serveur
    if data.temperature > TEMP_MAX:
        print("ALERTE ROUGE : Dépassement de seuil critique (> 8°C) !")
        status = "ALERTE"
    else:
        status = "NORMAL"
 
    record = {
        "device_id": data.device_id,
        "transport_id": data.transport_id,
        "temperature": data.temperature,
        "humidity": data.humidity,
        "lat": data.lat,
        "lon": data.lon,
        "status": status,
        "timestamp": _naive_utc(data.timestamp) if data.timestamp else datetime.utcnow(),
    }
 
    result = await temperature_collection.insert_one(record)
 
    return {
        "status": "success",
        "temperature_status": status,
        "received_value": data.temperature,
        "db_id": str(result.inserted_id),
    }
 
 
@app.get("/api/temperatures")
async def get_temperatures(limit: int = Query(50, le=2000)):
    """Dernières mesures, la plus récente en premier (compatible avec vos app.py / dashboard.py)."""
    cursor = temperature_collection.find().sort("timestamp", -1).limit(limit)
    records = await cursor.to_list(length=limit)
    return [_clean(r) for r in records]
 
 
@app.get("/api/measurements")
async def get_measurements(transport_id: Optional[str] = None, limit: int = Query(200, le=2000)):
    """Mesures d'un transport en ordre chronologique (pour la courbe et la trajectoire GPS)."""
    cursor = temperature_collection.find(_filter(transport_id)).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    docs.reverse()
    return [_clean(d) for d in docs]
 
 
@app.get("/api/latest")
async def get_latest(transport_id: Optional[str] = None):
    doc = await temperature_collection.find_one(_filter(transport_id), sort=[("timestamp", -1)])
    return _clean(doc) if doc else {}
 
 
@app.get("/api/risk")
async def get_risk(transport_id: Optional[str] = None):
    n = WINDOW * 20
    cursor = temperature_collection.find(_filter(transport_id)).sort("timestamp", -1).limit(n)
    docs = await cursor.to_list(length=n)
    docs.reverse()
    return compute_risk(docs)
 
 
@app.get("/api/transports")
async def get_transports():
    """Historique des transports : un résumé par transport_id, le plus récent d'abord."""
    pipeline = [
        {"$group": {
            "_id": {"$ifNull": ["$transport_id", DEFAULT_TRANSPORT]},
            "start": {"$min": "$timestamp"},
            "end": {"$max": "$timestamp"},
            "count": {"$sum": 1},
            "max_temp": {"$max": "$temperature"},
            "alerts": {"$sum": {"$cond": [{"$gt": ["$temperature", TEMP_MAX]}, 1, 0]}},
        }},
        {"$sort": {"end": -1}},
    ]
    out = []
    async for r in temperature_collection.aggregate(pipeline):
        out.append({
            "transport_id": r["_id"],
            "start": r["start"].isoformat() + "Z",
            "end": r["end"].isoformat() + "Z",
            "count": r["count"],
            "max_temp": r["max_temp"],
            "alerts": r["alerts"],
            "conforme": r["alerts"] == 0,
        })
    return out
 
 
# --- POUR RENDER ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
 