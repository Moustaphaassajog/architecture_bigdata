from pymongo import MongoClient

MONGO_URI = "mongodb://admin:motdepasse@localhost:27017/"
DB_NAME = "kbo_db"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

NACE_HOTELLERIE = [
    "55100", "55201", "55202", "55203", "55204",
    "55209", "55300", "55400", "55900",
]

JURIDICAL_FORM_EXCLUS = [
    "110", "114", "116", "117",           # entités publiques
    "301", "302", "303",                   # services fédéraux
    "310", "320", "330", "340", "350",     # autorités régionales
    "400", "411", "412", "413", "414",     # communes, CPAS, intercommunales
    "415", "416", "417", "418", "419", "420",
]


def find_entreprises_hotelieres() -> list[dict]:
    """Filtre enterprise_finale (entreprises_full) selon les critères hôtellerie."""
    source = db["entreprises_full"]

    pipeline = [
        {
            "$match": {
                "Status": "AC",
                "TypeOfEnterprise": "2",
                "JuridicalForm": {"$nin": JURIDICAL_FORM_EXCLUS},
                "activities": {
                    "$elemMatch": {
                        "Classification": "MAIN",
                        "NaceCode": {"$in": NACE_HOTELLERIE}
                    }
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "EnterpriseNumber": 1,
                "JuridicalForm": 1,
                "Status": 1,
                "activities": 1,
            }
        }
    ]

    return list(source.aggregate(pipeline))


if __name__ == "__main__":
    entreprises = find_entreprises_hotelieres()
    print(f"{len(entreprises)} entreprises hôtelières trouvées.")

    if entreprises:
        print("\nExemple :")
        print(entreprises[0])

    # Sauvegarde dans une collection dédiée pour la suite du pipeline
    target = db["entreprises_hotellerie"]
    target.drop()
    if entreprises:
        target.insert_many(entreprises)
        target.create_index("EnterpriseNumber", unique=True)
    print(f"\nCollection 'entreprises_hotellerie' créée avec {len(entreprises)} documents.")