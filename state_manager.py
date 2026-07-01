from pymongo import MongoClient
from datetime import datetime, timezone

MONGO_URI = "mongodb://admin:motdepasse@localhost:27017/"
DB_NAME = "kbo_db"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
state_coll = db["download_state"]


def deja_traite(bce_number: str, deposit_id: str, type_document: str) -> bool:
    """True si ce document a déjà été téléchargé avec succès."""
    return state_coll.find_one({
        "bce_number": bce_number,
        "deposit_id": str(deposit_id),
        "type_document": type_document,
        "statut": "done"
    }) is not None


def marquer_pending(bce_number: str, deposit_id: str, type_document: str, annee: int = None):
    """Crée ou remet une entrée en 'pending' avant tentative de téléchargement."""
    now = datetime.now(timezone.utc)
    state_coll.update_one(
        {"bce_number": bce_number, "deposit_id": str(deposit_id), "type_document": type_document},
        {
            "$set": {"annee": annee, "statut": "pending", "timestamp_maj": now},
            "$setOnInsert": {
                "timestamp_creation": now,
                "chemin_hdfs": None,
                "erreur_message": None,
                "tentatives": 0
            }
        },
        upsert=True
    )


def marquer_done(bce_number: str, deposit_id: str, type_document: str, chemin_hdfs: str):
    """Marque un document comme correctement téléchargé et stocké."""
    state_coll.update_one(
        {"bce_number": bce_number, "deposit_id": str(deposit_id), "type_document": type_document},
        {"$set": {
            "statut": "done",
            "chemin_hdfs": chemin_hdfs,
            "timestamp_maj": datetime.now(timezone.utc),
            "erreur_message": None
        }}
    )


def marquer_error(bce_number: str, deposit_id: str, type_document: str, message: str):
    """Marque un échec et incrémente le compteur de tentatives."""
    state_coll.update_one(
        {"bce_number": bce_number, "deposit_id": str(deposit_id), "type_document": type_document},
        {
            "$set": {
                "statut": "error",
                "erreur_message": message,
                "timestamp_maj": datetime.now(timezone.utc)
            },
            "$inc": {"tentatives": 1}
        }
    )