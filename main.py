from fastapi import FastAPI
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os

app = FastAPI()

# Connexion à MongoDB (utilise une variable d'environnement si elle existe, sinon localhost par défaut)
MONGO_DETAILS = os.environ.get("MONGO_DETAILS", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.smart_cold_chain
temperature_collection = database.get_collection("temperatures")

class TemperatureData(BaseModel):
    temperature: float
    device_id: str
@app.get("/")
def read_root():
    return {"message": "Smart Cold Chain API is live and running!"}

@app.post("/api/temperature")
async def receive_temperature(data: TemperatureData):
    print(f"[{data.device_id}] Température reçue : {data.temperature} °C")

    # Logique d'alerte côté serveur
    if data.temperature > 8.0:
        print("ALERTE ROUGE : Dépassement de seuil critique (> 8°C) !")
        status = "ALERTE"
    else:
        status = "NORMAL"

    record = {
        "device_id": data.device_id,
        "temperature": data.temperature,
        "status": status,
        "timestamp": datetime.utcnow()
    }

    # Insertion asynchrone dans MongoDB
    result = await temperature_collection.insert_one(record)

    return {
        "status": "success",
        "temperature_status": status,
        "received_value": data.temperature,
        "db_id": str(result.inserted_id)
    }

@app.get("/api/temperatures")
async def get_temperatures(limit: int = 50):
    cursor = temperature_collection.find().sort("_id", -1).limit(limit)
    records = await cursor.to_list(length=limit)
    
    # Convertir les ObjectId en string pour le format JSON
    for record in records:
        record["_id"] = str(record["_id"])
    return records 

# --- AJOUT IMPORTANT POUR RENDER ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

    @app.get("/api/temperatures", response_description="Lister toutes les températures")
async def get_temperatures():
    # Récupère tous les documents de ta collection (adapte le nom de ta collection si besoin)
    temperatures = []
    async for temp in db["temperatures"].find():
        # Convertit l'ID MongoDB en string pour éviter les erreurs de sérialisation JSON
        temp["id"] = str(temp["_id"])
        del temp["_id"]
        temperatures.append(temp)
    
    return {"status": "success", "data": temperatures}