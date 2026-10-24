"""
firebase_client.py : envoie la température et la position en temps réel vers Firebase Realtime Database.
 
Variables d'environnement :
    FIREBASE_DB_URL            ex. https://smart-cold-chain-default-rtdb.firebaseio.com
    FIREBASE_CREDENTIALS       contenu complet du fichier JSON de la clé de service (utile sur Render)
    FIREBASE_CREDENTIALS_FILE  ou chemin du fichier JSON (utile en local)
 
Si rien n'est configuré, les fonctions ne font rien et l'API continue de marcher (MongoDB seul).
"""
import json
import os
import re
from datetime import datetime
 
from starlette.concurrency import run_in_threadpool
 
_db = None
_ready = False
 
 
def _init() -> None:
    global _db, _ready
    url = os.environ.get("FIREBASE_DB_URL")
    cred_json = os.environ.get("FIREBASE_CREDENTIALS")
    cred_file = os.environ.get("FIREBASE_CREDENTIALS_FILE")
    if not url or not (cred_json or cred_file):
        print("ℹ️ Firebase non configuré : envoi temps réel désactivé")
        return
    try:
        import firebase_admin
        from firebase_admin import credentials, db
 
        cred = credentials.Certificate(json.loads(cred_json) if cred_json else cred_file)
        firebase_admin.initialize_app(cred, {"databaseURL": url})
        _db, _ready = db, True
        print("✅ Firebase connecté")
    except Exception as e:
        print(f"⚠️ Initialisation Firebase impossible : {e}")
 
 
_init()
 
 
def _key(value: str) -> str:
    # Firebase interdit . $ # [ ] / dans les clés
    return re.sub(r"[.$#\[\]/]", "_", value)
 
 
def _iso(ts) -> str:
    return ts.isoformat() + "Z" if isinstance(ts, datetime) else str(ts)
 
 
def _write(record: dict) -> None:
    tid = _key(record.get("transport_id", "TRANSPORT_1"))
    point = {
        "temperature": record["temperature"],
        "humidity": record.get("humidity"),
        "lat": record.get("lat"),
        "lon": record.get("lon"),
        "status": record["status"],
        "device_id": record["device_id"],
        "timestamp": _iso(record["timestamp"]),
    }
    _db.reference(f"live/{tid}").set(point)                       # état actuel du véhicule
    if point["lat"] is not None and point["lon"] is not None:
        _db.reference(f"tracks/{tid}").push(                       # trajectoire GPS
            {k: point[k] for k in ("lat", "lon", "temperature", "timestamp")})
 
 
async def push_live(record: dict) -> bool:
    """Retourne True si l'envoi a réussi. Ne lève jamais d'exception."""
    if not _ready:
        return False
    try:
        await run_in_threadpool(_write, record)
        return True
    except Exception as e:
        print(f"⚠️ Envoi Firebase échoué : {e}")
        return False
 