from pymongo import MongoClient
from mongo_utils import count_total_entreprises

MONGO_URI = "mongodb://admin:motdepasse@localhost:27017/"
DB_NAME = "kbo_db"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
state_coll = db["download_state"]


def print_report():
    total_entreprises = count_total_entreprises()

    print("=" * 60)
    print("RAPPORT D'AVANCEMENT — PIPELINE KBO")
    print("=" * 60)
    print(f"Total entreprises dans entreprises_full : {total_entreprises}")
    print()

    for type_doc in ["comptes_annuels", "statuts", "comptes_annuels_hotellerie"]:
        print(f"--- {type_doc} ---")
        done        = state_coll.count_documents({"type_document": type_doc, "statut": "done"})
        pending     = state_coll.count_documents({"type_document": type_doc, "statut": "pending"})
        in_progress = state_coll.count_documents({"type_document": type_doc, "statut": "in_progress"})
        error       = state_coll.count_documents({"type_document": type_doc, "statut": "error"})
        total       = done + pending + in_progress + error
        print(f"  done        : {done}")
        print(f"  pending     : {pending}")
        print(f"  in_progress : {in_progress}")
        print(f"  error       : {error}")
        print(f"  total       : {total}")
        print()

    print("--- Erreurs les plus fréquentes (top 5, toutes catégories) ---")
    pipeline = [
        {"$match": {"statut": "error"}},
        {"$group": {"_id": "$erreur_message", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    for err in state_coll.aggregate(pipeline):
        print(f"  [{err['count']}x] {err['_id']}")

    print("=" * 60)


if __name__ == "__main__":
    print_report()