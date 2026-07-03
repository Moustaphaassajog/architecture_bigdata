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


def marquer_in_progress(bce_number: str, deposit_id: str, type_document: str):
    """Marque une entrée comme en cours de traitement (évite les retraitements concurrents)."""
    now = datetime.now(timezone.utc)
    state_coll.update_one(
        {"bce_number": bce_number, "deposit_id": str(deposit_id), "type_document": type_document},
        {
            "$set": {"statut": "in_progress", "timestamp_maj": now},
            "$setOnInsert": {
                "timestamp_creation": now,
                "chemin_hdfs": None,
                "erreur_message": None,
                "tentatives": 0
            }
        },
        upsert=True
    )


def marquer_done(bce_number: str, deposit_id: str, type_document: str, chemin_hdfs: str = None, filings_count: int = None):
    """Marque un document (ou une entreprise entière) comme correctement traité."""
    update_fields = {
        "statut": "done",
        "timestamp_maj": datetime.now(timezone.utc),
        "erreur_message": None
    }
    if chemin_hdfs is not None:
        update_fields["chemin_hdfs"] = chemin_hdfs
    if filings_count is not None:
        update_fields["filings_count"] = filings_count

    state_coll.update_one(
        {"bce_number": bce_number, "deposit_id": str(deposit_id), "type_document": type_document},
        {"$set": update_fields}
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