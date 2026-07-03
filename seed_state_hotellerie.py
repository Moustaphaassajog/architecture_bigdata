from pymongo import MongoClient
from datetime import datetime, timezone

MONGO_URI = "mongodb://admin:motdepasse@localhost:27017/"
DB_NAME = "kbo_db"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

state_coll = db["download_state"]
hotellerie_coll = db["entreprises_hotellerie"]


def _clean_bce(bce: str) -> str:
    return bce.replace(".", "").strip()


def seed_hotellerie():
    entreprises = list(hotellerie_coll.find({}, {"EnterpriseNumber": 1, "_id": 0}))
    print(f"{len(entreprises)} entreprises hôtelières à seeder dans download_state.")

    now = datetime.now(timezone.utc)
    inserted, already_exist = 0, 0

    for ent in entreprises:
        bce = _clean_bce(ent["EnterpriseNumber"])

        result = state_coll.update_one(
            {"bce_number": bce, "deposit_id": "ALL", "type_document": "comptes_annuels_hotellerie"},
            {
                "$setOnInsert": {
                    "annee": None,
                    "statut": "pending",
                    "chemin_hdfs": None,
                    "erreur_message": None,
                    "tentatives": 0,
                    "filings_count": 0,
                    "timestamp_creation": now,
                    "timestamp_maj": now,
                }
            },
            upsert=True
        )

        if result.upserted_id:
            inserted += 1
        else:
            already_exist += 1

    print(f"Termine : {inserted} nouvelles entrees 'pending', {already_exist} deja presentes.")


if __name__ == "__main__":
    seed_hotellerie()