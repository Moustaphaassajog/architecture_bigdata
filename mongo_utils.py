from pymongo import MongoClient

MONGO_URI = "mongodb://admin:motdepasse@localhost:27017/"
DB_NAME = "kbo_db"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Palier de validation — mettre None pour traiter l'ensemble des entreprises
LIMIT_TEST = 10


def _clean_bce(bce: str) -> str:
    """Retire les points du format BCE (ex: '0200.065.765' -> '0200065765')."""
    return bce.replace(".", "").strip()


def get_all_bce_numbers() -> list[str]:
    """Retourne la liste des numéros BCE (nettoyés) présents dans entreprises_full."""
    cursor = db["entreprises_full"].find({}, {"EnterpriseNumber": 1, "_id": 0})
    if LIMIT_TEST:
        cursor = cursor.limit(LIMIT_TEST)
    return [_clean_bce(doc["EnterpriseNumber"]) for doc in cursor if doc.get("EnterpriseNumber")]


def get_all_entreprises() -> list[dict]:
    """Retourne BCE (nettoyés) + forme juridique + statut."""
    cursor = db["entreprises_full"].find(
        {}, {"EnterpriseNumber": 1, "JuridicalForm": 1, "Status": 1, "_id": 0}
    )
    if LIMIT_TEST:
        cursor = cursor.limit(LIMIT_TEST)
    entreprises = list(cursor)
    for ent in entreprises:
        if ent.get("EnterpriseNumber"):
            ent["EnterpriseNumber"] = _clean_bce(ent["EnterpriseNumber"])
    return entreprises


def count_total_entreprises() -> int:
    """Retourne le nombre total d'entreprises dans entreprises_full (sans limite)."""
    return db["entreprises_full"].count_documents({})